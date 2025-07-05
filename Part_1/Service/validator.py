from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import re
from Core.log_config import get_module_logger

logger = get_module_logger(__name__)


class Validator:

    def __init__(self):
        
        self.required_fields = [
            'lastName', 
            'firstName', 
            'idNumber', 
            'dateOfInjury',
            'accidentDescription', 
            'injuredBodyPart'
        ]
        
        self.date_fields = [
            'dateOfBirth', 
            'dateOfInjury', 
            'formFillingDate', 
            'formReceiptDateAtClinic'
        ]
        
        self.phone_fields = [
            'landlinePhone',
            'mobilePhone'
        ]
        
        self.text_fields = [
            'accidentDescription', 
            'firstName', 
            'lastName', 
            'jobType'
        ]

        self.address_fields = ['street', 'houseNumber', 'entrance', 'apartment', 'city', 'postalCode', 'poBox']

        logger.info("Validation Service initialized")


    # --------------- validations ------------------------------------------------------------------------------

    def valid_extraction(self, extracted_data: Dict, ground_truth: Optional[Dict] = None) -> Dict:
        
        logger.info("Starting comprehensive validation")
    
        results = {
            "is_valid": True,
            "validation_errors": [],
            "field_level_validation": {},
            "completeness_score": 0.0,
            "accuracy_score": None,
            "confidence_scores": {},
            "summary": {}
        }
        
        # ------ scheme -------------------------

        schema_validation = self.valid_schema(extracted_data)
        results["schema_valid"] = schema_validation["is_valid"]
        results["validation_errors"].extend(schema_validation["errors"])
        logger.debug(f"Schema validation: {'PASSED' if schema_validation['is_valid'] else 'FAILED'}")
    
        
        # ------ field -------------------------

        field_validation = self.valid_fields(extracted_data)
        results["field_level_validation"] = field_validation
        failed_fields = [field for field, details in field_validation.items() if not details.get('is_valid', True)]
    
        if failed_fields:
            logger.warning(f"Field validation failed for: {failed_fields}")
        
        # ------ completeness -------------------------

        completeness = self.completeness(extracted_data)
        results["completeness_score"] = completeness["score"]
        results["summary"]["total_fields"] = completeness["total_fields"]
        results["summary"]["filled_fields"] = completeness["filled_fields"]
        results["summary"]["missing_required_fields"] = completeness["missing_required"]
        logger.info(f"Completeness score: {completeness['score']:.2%}")
        
        # ------ confidence -------------------------

        confidence = self.confidence(extracted_data)
        results["confidence_scores"] = confidence

        # ------ section metrics -------------------------
        
        section_metrics = self.section_metrics(extracted_data)
        results["section_metrics"] = section_metrics
        
        # ------ overall -------------------------

        results["is_valid"] = (
            schema_validation["is_valid"] and 
            len(completeness["missing_required"]) == 0 and
            len(results["validation_errors"]) == 0
        )
        
        logger.info(f"Validation completed. Valid: {results['is_valid']}, "f"Completeness: {completeness['score']:.2%}")
        
        return results
    
    def valid_schema(self, data: Dict) -> Dict:

        # ------ actual schema ------------------------------------

        errors = []
        expected_fields = [
            'lastName',
            'firstName',
            'idNumber',
            'gender',
            'dateOfBirth',
            'address',
            'landlinePhone',
            'mobilePhone',
            'jobType',
            'dateOfInjury',
            'timeOfInjury',
            'accidentLocation',
            'accidentAddress',
            'accidentDescription',
            'injuredBodyPart',
            'signature',
            'formFillingDate',
            'formReceiptDateAtClinic',
            'medicalInstitutionFields'
        ]
        
        # ------ missing fields ------------------------------------

        for field in expected_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # ------ nested structures ------------------------------------

        if 'address' in data and isinstance(data['address'], dict):
            for field in self.address_fields:
                if field not in data['address']:
                    errors.append(f"Missing address field: {field}")
        
        for date_field in self.date_fields:
            if date_field in data and isinstance(data[date_field], dict):
                for part in ['day', 'month', 'year']:
                    if part not in data[date_field]:
                        errors.append(f"Missing {part} in {date_field}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    def valid_fields(self, data: Dict) -> Dict:
        
        field_validation = {}
        
        # ------ id -------------------------

        if 'idNumber' in data:

            id_valid = self.valid_id(data['idNumber'])
            
            field_validation['idNumber'] = \
            {
                "is_valid": id_valid,
                "value": data['idNumber'],
                "error": None if id_valid else "ID number must be 9 digits"
            }
        
        # ------ phone -------------------------

        for phone_field in self.phone_fields:
            
            if phone_field in data and data[phone_field]:
                
                phone_valid = self.valid_phone(data[phone_field])
                
                field_validation[phone_field] = \
                {
                    "is_valid": phone_valid,
                    "value": data[phone_field],
                    "error": None if phone_valid else "Invalid phone number format"
                }
        
        # ------ date -------------------------

        for date_field in self.date_fields:

            if date_field in data and isinstance(data[date_field], dict):
                
                date_valid = self.valid_date(data[date_field])
                
                field_validation[date_field] = \
                {
                    "is_valid": date_valid,
                    "value": data[date_field],
                    "error": None if date_valid else "Invalid date format"
                }
        
        # ------ gender -------------------------

        if 'gender' in data and data['gender']:

            gender_valid = data['gender'].lower() in ['זכר', 'נקבה', 'male', 'female', 'מ', 'ז', 'נ', 'ב']

            field_validation['gender'] = \
            {
                "is_valid": gender_valid,
                "value": data['gender'],
                "error": None if gender_valid else "Invalid gender value"
            }
        
        return field_validation

    def valid_id(self, id_number: str) -> bool:
       
        if not id_number:
            return False
        
        # non digits
        clean_id = re.sub(r'\D', '', id_number)
        
        # invalid ID
        if len(clean_id) != 9:
            return False
        
        # optimization : add Luhn algorithm
        return True
    
    def valid_phone(self, phone: str) -> bool:
        
        if not phone:
            return False
        
        # non digit
        clean_phone = re.sub(r'\D', '', phone)
        
        # length check
        if not (9 <= len(clean_phone) <= 10):
            return False
        
        # start with 0
        if not clean_phone.startswith('0'):
            return False
        
        return True
    
    def valid_date(self, date_dict: Dict) -> bool:

        try:

            day = date_dict.get('day', '')
            month = date_dict.get('month', '')
            year = date_dict.get('year', '')
            
            # ------ present validation -----------------------

            if not all([day, month, year]):
                return False
            
            # ------ numeric validation -----------------------
            
            if not all([day.isdigit(), month.isdigit(), year.isdigit()]):
                return False
            
            # ------ convert to int -----------------------

            day_int = int(day)
            month_int = int(month)
            year_int = int(year)
            
            # ------ range validation -----------------------

            if not (1 <= day_int <= 31):
                return False
            if not (1 <= month_int <= 12):
                return False
            if not (1900 <= year_int <= 2100):
                return False
            
            datetime(year_int, month_int, day_int)

            return True
            

        except (ValueError, AttributeError):
            return False
    

    # --------------- validations ------------------------------------------------------------------------------

    def completeness(self, data: Dict) -> Dict:
       
        field_total = 0
        field_valid = 0
        field_empty = []
        field_missing = []
        
        def count(file_data, prefix=""):

            nonlocal field_total, field_valid, field_empty
            
            if isinstance(file_data, dict):

                for key, value in file_data.items():

                    # ------ count -----------------------
                    
                    field_name = f"{prefix}.{key}" if prefix else key
                    field_total += 1
                    
                    # ------ nested -----------------------

                    if isinstance(value, dict):
                        count(value, field_name)
                    
                    # ------ field -----------------------

                    elif value and str(value).strip():
                        field_valid += 1

                    # ------ empty / missing -----------------------

                    else:
                        field_empty.append(field_name)
                        if key in self.required_fields:
                            field_missing.append(key)

            elif file_data and str(file_data).strip():
                field_valid += 1

            else:
                field_total += 1
                field_empty.append(prefix)
        
        count(data)
        
        score = field_valid / field_total if field_total > 0 else 0
        
        return {
            "score": score,
            "total_fields": field_total,
            "filled_fields": field_valid,
            "empty_fields": field_empty,
            "missing_required": field_missing
        }
    
    def accuracy(self, extracted_data: Dict, ground_truth: Dict) -> Dict:
        
        total_comparisons = 0
        correct_fields = 0
        field_accuracy = {}
        
        def compare(extracted, truth, field_path=""):

            nonlocal total_comparisons, correct_fields
            
            if isinstance(extracted, dict) and isinstance(truth, dict):
                for key in truth.keys():
                    if key in extracted:
                        field_name = f"{field_path}.{key}" if field_path else key
                        compare(extracted[key], truth[key], field_name)

            else:
                
                total_comparisons += 1
                extracted_str = str(extracted).strip().lower()
                truth_str = str(truth).strip().lower()
                
                is_correct = extracted_str == truth_str
                if is_correct:
                    correct_fields += 1
                
                field_accuracy[field_path] = {
                    "extracted": str(extracted),
                    "ground_truth": str(truth),
                    "is_correct": is_correct
                }
        
        compare(extracted_data, ground_truth)
        
        overall_accuracy = correct_fields / total_comparisons if total_comparisons > 0 else 0
        
        return {
            "overall_accuracy": overall_accuracy,
            "total_fields": total_comparisons,
            "correct_fields": correct_fields,
            "field_accuracy": field_accuracy
        }
    
    def confidence(self, data: Dict) -> Dict:
        
        confidence_scores = {}
        
        # ------ ID -----------------------

        if 'idNumber' in data and data['idNumber']:
            id_conf = 1.0 if len(data['idNumber']) == 9 and data['idNumber'].isdigit() else 0.5
            confidence_scores['idNumber'] = id_conf
        
        # ------ phone -----------------------

        for phone in ['landlinePhone', 'mobilePhone']:
            if phone in data and data[phone]:
                phone = re.sub(r'\D', '', data[phone])
                
                if len(phone) == 10 and phone.startswith('0'):
                    confidence_scores[phone] = 1.0
                
                elif 9 <= len(phone) <= 10:
                    confidence_scores[phone] = 0.8
                
                else:
                    confidence_scores[phone] = 0.3
        
        # ------ date -----------------------

        for date in self.date_fields:
            if date in data and isinstance(data[date], dict):
                date_dict = data[date]
                
                if all(date_dict.get(part, '').isdigit() for part in ['day', 'month', 'year']):
                    confidence_scores[date] = 0.9
                
                else:
                    confidence_scores[date] = 0.4
        
        # ------ date -----------------------

        for field in self.text_fields:
            if field in data and data[field]:
                text_len = len(data[field])
                if text_len > 2:
                    confidence_scores[field] = min(0.5 + (text_len / 100), 1.0)
                else:
                    confidence_scores[field] = 0.3
        
        return confidence_scores
    
    def section_metrics(self, data: Dict) -> Dict:
        
        # ------ sections ----------------------------------------------------------

        logger.info("Calculating section-based metrics")
        
        sections = {
            "פרטים אישיים": {
                "fields": ["lastName", "firstName", "idNumber", "gender", "dateOfBirth"],
                "filled": 0,
                "total": 0
            },
            "פרטי קשר": {
                "fields": ["address", "landlinePhone", "mobilePhone"],
                "filled": 0,
                "total": 0
            },
            "תעסוקה": {
                "fields": ["jobType"],
                "filled": 0,
                "total": 0
            },
            "פרטי התאונה": {
                "fields": ["dateOfInjury", "timeOfInjury", "accidentLocation", 
                          "accidentAddress", "accidentDescription", "injuredBodyPart"],
                "filled": 0,
                "total": 0
            },
            "למילוי ע״י המוסד הרפואי": {
                "fields": ["medicalInstitutionFields"],
                "filled": 0,
                "total": 0
            },
            "שדות נוספים": {
                "fields": ["signature", "formFillingDate", "formReceiptDateAtClinic"],
                "filled": 0,
                "total": 0
            }
        }
        
        
        # ------ count filled sections ----------------------------------------------------------

        for section_name, section_info in sections.items():
            for field in section_info["fields"]:
                if field in data:
                    section_info["total"] += 1
                    
                    if field == "dateOfBirth" and isinstance(data[field], dict):
                        date_dict = data[field]
                        if all(date_dict.get(part, '') for part in ['day', 'month', 'year']):
                            section_info["filled"] += 1
                    
                    elif field == "address" and isinstance(data[field], dict):
                        addr = data[field]
                        if addr.get('street', '') and addr.get('city', ''):
                            section_info["filled"] += 1
                    
                    elif field == "dateOfInjury" and isinstance(data[field], dict):
                        date_dict = data[field]
                        if all(date_dict.get(part, '') for part in ['day', 'month', 'year']):
                            section_info["filled"] += 1
                    
                    elif field == "formFillingDate" and isinstance(data[field], dict):
                        date_dict = data[field]
                        if all(date_dict.get(part, '') for part in ['day', 'month', 'year']):
                            section_info["filled"] += 1
                    
                    elif field == "formReceiptDateAtClinic" and isinstance(data[field], dict):
                        date_dict = data[field]
                        if all(date_dict.get(part, '') for part in ['day', 'month', 'year']):
                            section_info["filled"] += 1
                    
                    elif field == "medicalInstitutionFields" and isinstance(data[field], dict):
                        med = data[field]
                        if any(med.get(f, '') for f in ['healthFundMember', 'natureOfAccident', 'medicalDiagnoses']):
                            section_info["filled"] += 1
                    
                    elif isinstance(data[field], str) and data[field].strip():
                        section_info["filled"] += 1
        
        # ------ sections ----------------------------------------------------------
        
        section_4 = sections["פרטי התאונה"]
        if section_4["filled"] < section_4["total"]:
            logger.warning(f"Critical Section 4 (פרטי התאונה) incomplete: {section_4['filled']}/{section_4['total']}")
        
        return {name: (info["filled"], info["total"]) for name, info in sections.items()}
    
    # --------------- report ------------------------------------------------------------------------------

    def report(self, results: Dict) -> str:
        
        report = []
        report.append("=== Form Validation Report ===\n")
        
        # ------ overall -----------------------

        status = "VALID" if results['is_valid'] else "INVALID"
        report.append(f"Overall Status: {status}")
        report.append(f"Completeness Score: {results['completeness_score']:.2%}")
        
        if results['accuracy_score'] is not None:
            report.append(f"Accuracy Score: {results['accuracy_score']:.2%}")
        
        # ------ date -----------------------
        
        report.append(f"\nSummary:")
        report.append(f"- Total Fields: {results['summary']['total_fields']}")
        report.append(f"- Filled Fields: {results['summary']['filled_fields']}")
        report.append(f"- Missing Required Fields: {len(results['summary']['missing_required_fields'])}")
        
        # ------ errors -----------------------
        
        if results['validation_errors']:
            report.append(f"\nValidation Errors:")
            for error in results['validation_errors']:
                report.append(f"- {error}")
        
        # ------ fields -----------------------
        
        if results['field_level_validation']:
            invalid_fields = [
                f"{field}: {details['error']}" 
                for field, details in results['field_level_validation'].items() 
                if not details['is_valid']
            ]
            if invalid_fields:
                report.append(f"\nField Validation Issues:")
                for issue in invalid_fields:
                    report.append(f"- {issue}")
        
        # ------ confidence -----------------------
        
        if results['confidence_scores']:
            report.append(f"\nConfidence Scores:")
            for field, score in sorted(results['confidence_scores'].items(), 
                                      key=lambda x: x[1], reverse=True):
                report.append(f"- {field}: {score:.2f}")
        
        return "\n".join(report)