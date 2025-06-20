from openai import AzureOpenAI
import json
import logging
from typing import Dict, Any, Optional
from Core.schema import Form
import re

from Core.log_config import get_module_logger

logger = get_module_logger(__name__)



class Extractor:


    def __init__(self, endpoint: str, key: str, version: str, name: str):

        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=version
        )

        self.name = name
        logger.info("Extraction Service initialized successfully")
    
    def extract_fields(self, ocr_data: Dict, retry_count: int = 0) -> Dict:
   
        logger.info(f"Starting field extraction (attempt {retry_count + 1})")
        logger.debug(f"OCR data contains {len(ocr_data.get('full_text', ''))} characters")

        system_prompt = self.system_prompt()
        user_prompt = self.extraction_prompt(ocr_data)
        
        logger.info("Sending extraction request to GPT-4o")
        logger.debug(f"Using model: {self.name}")
        
        # -------- infer --------------------------------------

        try :
            response = self.client.chat.completions.create(
                model=self.name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"},
                max_tokens=2000
            )

            logger.info("Received response from GPT-4o")
            logger.debug(f"Response tokens used: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")
            
            extracted = json.loads(response.choices[0].message.content)
            logger.info("Successfully parsed JSON response")
            
            cleaned = self.clean(extracted)
            logger.info("Data cleaning completed successfully")
            
            logger.info("Field extraction completed successfully")
            return cleaned.output()
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Error during field extraction: {str(e)}", exc_info=True)
            raise
            
    # --------------- prompts ------------------------------------------------------------------------------

    def system_prompt(self) -> str:
       
        return """You are an expert at extracting information from Israeli National Insurance (ביטוח לאומי) forms.
        
                    Your task is to extract specific fields from the OCR text provided. The forms may be in Hebrew or English.

                    Important guidelines:
                    1. Extract ONLY the information explicitly present in the form.
                    2. For missing fields, use empty string "".
                    3. Maintain the exact spelling and format from the original text.
                    4. For dates, extract day, month, and year separately
                    5. For Hebrew text, preserve the original Hebrew characters
                    6. Gender should be extracted as found (זכר/נקבה or male/female)
                    7. ID numbers should be 9 digits when complete
                    8. Phone numbers should include all digits as shown

                    You must return a valid JSON object with the following structure:
                    {
                        "lastName": "",
                        "firstName": "",
                        "idNumber": "",
                        "gender": "",
                        "dateOfBirth": {"day": "", "month": "", "year": ""},
                        "address": {
                            "street": "",
                            "houseNumber": "",
                            "entrance": "",
                            "apartment": "",
                            "city": "",
                            "postalCode": "",
                            "poBox": ""
                        },
                        "landlinePhone": "",
                        "mobilePhone": "",
                        "jobType": "",
                        "dateOfInjury": {"day": "", "month": "", "year": ""},
                        "timeOfInjury": "",
                        "accidentLocation": "",
                        "accidentAddress": "",
                        "accidentDescription": "",
                        "injuredBodyPart": "",
                        "signature": "",
                        "formFillingDate": {"day": "", "month": "", "year": ""},
                        "formReceiptDateAtClinic": {"day": "", "month": "", "year": ""},
                        "medicalInstitutionFields": {
                            "healthFundMember": "",
                            "natureOfAccident": "",
                            "medicalDiagnoses": ""
                        }
                    }

                    Hebrew field mappings:
                    - שם משפחה = lastName
                    - שם פרטי = firstName
                    - מספר זהות / ת.ז. = idNumber
                    - מין = gender
                    - תאריך לידה = dateOfBirth
                    - כתובת = address (רחוב=street, מספר בית=houseNumber, כניסה=entrance, דירה=apartment, ישוב=city, מיקוד=postalCode)
                    - טלפון קווי = landlinePhone
                    - טלפון נייד = mobilePhone
                    - סוג העבודה = jobType
                    - תאריך הפגיעה = dateOfInjury
                    - שעת הפגיעה = timeOfInjury
                    - מקום התאונה = accidentLocation
                    - כתובת מקום התאונה = accidentAddress
                    - תיאור התאונה / נסיבות הפגיעה = accidentDescription
                    - האיבר שנפגע = injuredBodyPart
                    - חתימה = signature
                    - תאריך מילוי הטופס = formFillingDate
                    - תאריך קבלת הטופס בקופה = formReceiptDateAtClinic
                    - חבר בקופת חולים = healthFundMember
                    - מהות התאונה = natureOfAccident
                    - אבחנות רפואיות = medicalDiagnoses"""
    
    def extraction_prompt(self, ocr_data: Dict) -> str:

        full_text = ocr_data.get('full_text', '')
        
        # ------- key value pairs ----------------------------
        
        key_value = ""
        if ocr_data.get('key_value_pairs'):
            key_value = "\n\nKey-Value Pairs found:\n"
            for kv in ocr_data['key_value_pairs']:
                key_value += f"- {kv['key']}: {kv['value']}\n"
        
        prompt = f"""Please extract all form fields from the following OCR text of an Israeli National Insurance form:

                    OCR TEXT:
                    {full_text}
                    {key_value}

                    Remember:
                    1. Extract only what is explicitly written
                    2. Use empty strings for missing fields
                    3. Preserve original language (Hebrew/English)
                    4. Return valid JSON only
                """
        
        return prompt

    # --------------- cleaning ------------------------------------------------------------------------------

    def clean(self, extracted_data: Dict) -> Form:
        
        logger.debug("Starting data cleaning and validation")
        
        # ----- nested ----------------------------------------

        if 'date_of_birth' in extracted_data and isinstance(extracted_data['date_of_birth'], dict):
            extracted_data['dateOfBirth'] = extracted_data.pop('date_of_birth')
        if 'date_of_injury' in extracted_data and isinstance(extracted_data['date_of_injury'], dict):
            extracted_data['dateOfInjury'] = extracted_data.pop('date_of_injury')
        if 'form_filling_date' in extracted_data and isinstance(extracted_data['form_filling_date'], dict):
            extracted_data['formFillingDate'] = extracted_data.pop('form_filling_date')
        if 'form_receipt_date_at_clinic' in extracted_data and isinstance(extracted_data['form_receipt_date_at_clinic'], dict):
            extracted_data['formReceiptDateAtClinic'] = extracted_data.pop('form_receipt_date_at_clinic')
        if 'medical_institution_fields' in extracted_data and isinstance(extracted_data['medical_institution_fields'], dict):
            extracted_data['medicalInstitutionFields'] = extracted_data.pop('medical_institution_fields')
            
        # ----- function calls ----------------------------------------

        if 'landlinePhone' in extracted_data:
            extracted_data['landlinePhone'] = self.clean_phone(extracted_data['landlinePhone'])
        if 'mobilePhone' in extracted_data:
            extracted_data['mobilePhone'] = self.clean_phone(extracted_data['mobilePhone'])
        if 'idNumber' in extracted_data:
            extracted_data['idNumber'] = self.clean_id(extracted_data['idNumber'])
        
        # ----- validate ----------------------------------------

        try:
            form_data = Form(**extracted_data)
            logger.debug("Form validation successful")
            return form_data
        
        except Exception as e:
            logger.error(f"Form validation failed: {str(e)}")
            raise        
    
    def clean_phone(self, phone: str) -> str:
        
        if not phone:
            return ""
        
        # remove non digit
        cleaned = re.sub(r'\D', '', str(phone))

        # valid phone
        if 9 <= len(cleaned) <= 10:
            return cleaned
        
        # invalid phone
        return ""  
    
    def clean_id(self, id_num: str) -> str:

        if not id_num:
            return ""
        
        # remove non-digit
        cleaned = re.sub(r'\D', '', str(id_num))

        # valid ID
        if len(cleaned) == 9:
            return cleaned
        
        # invalid ID
        return ""  
    
