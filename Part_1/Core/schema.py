from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class Date(BaseModel):

    day: str = ""
    month: str = ""
    year: str = ""
    
    @field_validator('day', 'month', 'year')
    @classmethod
    def validate_date_field(cls, v):
        if v and not v.isdigit():
            return ""
        return v
    
class Address(BaseModel):
    street: str = ""
    houseNumber: str = Field(default="", alias="house_number")
    entrance: str = ""
    apartment: str = ""
    city: str = ""
    postalCode: str = Field(default="", alias="postal_code")
    poBox: str = Field(default="", alias="po_box")

class Medical(BaseModel):
    healthFundMember: str = Field(default="", alias="health_fund_member")
    natureOfAccident: str = Field(default="", alias="nature_of_accident")
    medicalDiagnoses: str = Field(default="", alias="medical_diagnoses")

class Form(BaseModel):
    lastName: str = Field(default="", alias="last_name")
    firstName: str = Field(default="", alias="first_name")
    idNumber: str = Field(default="", alias="id_number")
    gender: str = ""
    dateOfBirth: Date = Field(default_factory=Date, alias="date_of_birth")
    address: Address = Field(default_factory=Address)
    landlinePhone: str = Field(default="", alias="landline_phone")
    mobilePhone: str = Field(default="", alias="mobile_phone")
    jobType: str = Field(default="", alias="job_type")
    dateOfInjury: Date = Field(default_factory=Date, alias="date_of_injury")
    timeOfInjury: str = Field(default="", alias="time_of_injury")
    accidentLocation: str = Field(default="", alias="accident_location")
    accidentAddress: str = Field(default="", alias="accident_address")
    accidentDescription: str = Field(default="", alias="accident_description")
    injuredBodyPart: str = Field(default="", alias="injured_body_part")
    signature: str = ""
    formFillingDate: Date = Field(default_factory=Date, alias="form_filling_date")
    formReceiptDateAtClinic: Date = Field(default_factory=Date, alias="form_receipt_date_at_clinic")
    medicalInstitutionFields: Medical = Field(
        default_factory=Medical, 
        alias="medical_institution_fields"
    )
    
    class Config:
        populate_by_name = True
        
    @field_validator('idNumber')
    @classmethod
    def validate_id_number(cls, v):
        if v and len(v) == 9 and v.isdigit():
            return v
        return ""
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v.lower() in ['זכר', 'נקבה', 'male', 'female', 'מ', 'ז', 'נ', 'ב']:
            return v
        return ""
    
    def output(self):
        
        return {

            "lastName": self.lastName,
            "firstName": self.firstName,
            "idNumber": self.idNumber,
            "gender": self.gender,

            "dateOfBirth": 
            {
                "day": self.dateOfBirth.day,
                "month": self.dateOfBirth.month,
                "year": self.dateOfBirth.year
            },

            "address": 
            {
                "street": self.address.street,
                "houseNumber": self.address.houseNumber,
                "entrance": self.address.entrance,
                "apartment": self.address.apartment,
                "city": self.address.city,
                "postalCode": self.address.postalCode,
                "poBox": self.address.poBox
            },

            "landlinePhone": self.landlinePhone,
            "mobilePhone": self.mobilePhone,
            "jobType": self.jobType,
            ""
            "dateOfInjury": 
            {
                "day": self.dateOfInjury.day,
                "month": self.dateOfInjury.month,
                "year": self.dateOfInjury.year
            },

            "timeOfInjury": self.timeOfInjury,
            "accidentLocation": self.accidentLocation,
            "accidentAddress": self.accidentAddress,
            "accidentDescription": self.accidentDescription,
            "injuredBodyPart": self.injuredBodyPart,
            "signature": self.signature,
            
            "formFillingDate": 
            {
                "day": self.formFillingDate.day,
                "month": self.formFillingDate.month,
                "year": self.formFillingDate.year
            },

            "formReceiptDateAtClinic": 
            {
                "day": self.formReceiptDateAtClinic.day,
                "month": self.formReceiptDateAtClinic.month,
                "year": self.formReceiptDateAtClinic.year
            },

            "medicalInstitutionFields": 
            {
                "healthFundMember": self.medicalInstitutionFields.healthFundMember,
                "natureOfAccident": self.medicalInstitutionFields.natureOfAccident,
                "medicalDiagnoses": self.medicalInstitutionFields.medicalDiagnoses
            }
        }