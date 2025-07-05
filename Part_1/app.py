import json
from datetime import datetime
import pandas as pd
from pathlib import Path
from PIL import Image
import streamlit as st

from Service.ocr import OCR
from Service.extractor import Extractor
from Service.validator import Validator

import Core.config as config
from Core.log_config import get_module_logger, setup_logging

# Initialize robust logging for production
setup_logging()

# ------------- logger ----------------------------------------------

logger = get_module_logger(__name__)

# ------------- resources ----------------------------------------------

@st.cache_resource
def services():
    
    logger.info("Initializing services...")
    
    ocr = OCR(
        endpoint=config.doc_int_endpoint,
        key=config.doc_int_key
    )
    
    extractor = Extractor(
        endpoint=config.openai_endpoint,
        key=config.openai_key,
        version=config.openai_version,
        name=config.openai_model
    )
    
    validator = Validator()

    logger.info("All services initialized successfully")
    
    return ocr, extractor, validator

def process(file_content: bytes, file_type: str, filename: str):
    
    # --- init ---------------------------------------------------------------

    logger.info(f"Starting document processing for file: {filename} (type: {file_type}, size: {len(file_content)} bytes)")

    ocr, extractor, validator = services()
    
    results = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "status": "processing"
    }
    
    # --- begin process ---------------------------------------------------------------

    try:
        
        # -------- ocr ----------------

        with st.spinner("מבצע OCR על המסמך..."):
            ocr_data = ocr.extract_text(file_content, file_type)
            results["ocr_success"] = True
            results["ocr_text_length"] = len(ocr_data.get('full_text', ''))
            logger.info(f"OCR completed successfully. Extracted {results['ocr_text_length']} characters")
        
        # -------- extractor ----------

        with st.spinner("מחלץ שדות מהמסמך..."):
            extracted_fields = extractor.extract_fields(ocr_data)
            results["extraction_success"] = True
            results["extracted_data"] = extracted_fields
            logger.info("Field extraction completed successfully")
        
        # -------- validator ----------

        with st.spinner("מאמת את הנתונים..."):
            validation_results = validator.valid_extraction(extracted_fields)
            results["validation"] = validation_results
            results["status"] = "completed"
            logger.info("Field extraction completed successfully")
        
    # --- process failed ---------------------------------------------------------------
 
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        results["status"] = "error"
        results["error"] = str(e)
        st.error(f"שגיאה בעיבוד המסמך: {str(e)}")

    logger.info(f"Document processing completed for {filename} with status: {results['status']}")

    return results

def display(results: dict):
        
    
    # -------------- status -----------------------------------------------

    if results["status"] == "completed":
        st.success("העיבוד הושלם בהצלחה!")

    elif results["status"] == "error":
        st.error(f"שגיאה בעיבוד: {results.get('error', 'Unknown error')}")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["נתונים מחולצים", "אימות", "מטריקות", "JSON"])
    
    # -------------- tab 1 - extracted fields  -----------------------------------------------

    with tab1:

        st.subheader("שדות שחולצו מהטופס")
        
        # --- personal / contact information  ------------------------
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### פרטים אישיים")
            data = results["extracted_data"]
            st.text_input("שם משפחה", value=data.get("lastName", ""), disabled=True)
            st.text_input("שם פרטי", value=data.get("firstName", ""), disabled=True)
            st.text_input("מספר זהות", value=data.get("idNumber", ""), disabled=True)
            st.text_input("מין", value=data.get("gender", ""), disabled=True)
            
            if "dateOfBirth" in data:
                dob = data["dateOfBirth"]
                st.text_input("תאריך לידה", 
                            value=f"{dob.get('day', '')}/{dob.get('month', '')}/{dob.get('year', '')}", 
                            disabled=True)

        with col2:

            st.markdown("### פרטי קשר")
            st.text_input("טלפון קווי", value=data.get("landlinePhone", ""), disabled=True)
            st.text_input("טלפון נייד", value=data.get("mobilePhone", ""), disabled=True)

            if "address" in data:
                addr = data["address"]
                
                st.text_input("רחוב", value=addr.get("street", ""), disabled=True)
                
                col_addr1, col_addr2, col_addr3 = st.columns(3)
                with col_addr1:
                    st.text_input("מספר בית", value=addr.get("houseNumber", ""), disabled=True)
                with col_addr2:
                    st.text_input("כניסה", value=addr.get("entrance", ""), disabled=True)
                with col_addr3:
                    st.text_input("דירה", value=addr.get("apartment", ""), disabled=True)

                st.text_input("עיר", value=addr.get("city", ""), disabled=True)
                st.text_input("מיקוד", value=addr.get("postalCode", ""), disabled=True)
        

        # --- accident information  ------------------------

        st.markdown("### פרטי התאונה")
        col3, col4 = st.columns(2)

        with col3:
            if "dateOfInjury" in data:
                doi = data["dateOfInjury"]
                st.text_input("תאריך הפגיעה", 
                            value=f"{doi.get('day', '')}/{doi.get('month', '')}/{doi.get('year', '')}", 
                            disabled=True)
            st.text_input("שעת הפגיעה", value=data.get("timeOfInjury", ""), disabled=True)
            st.text_input("מקום התאונה", value=data.get("accidentLocation", ""), disabled=True)
        
        with col4:
            st.text_input("כתובת מקום התאונה", value=data.get("accidentAddress", ""), disabled=True)
            st.text_input("האיבר שנפגע", value=data.get("injuredBodyPart", ""), disabled=True)
            st.text_input("סוג העבודה", value=data.get("jobType", ""), disabled=True)
        
        st.text_area("תיאור התאונה", value=data.get("accidentDescription", ""), disabled=True, height=100)
        
        # --- medical information  ------------------------

        if "medicalInstitutionFields" in data:
            st.markdown("### למילוי ע״י המוסד הרפואי")
            med = data["medicalInstitutionFields"]
            st.text_input("חבר בקופת חולים", value=med.get("healthFundMember", ""), disabled=True)
            st.text_input("מהות התאונה", value=med.get("natureOfAccident", ""), disabled=True)
            st.text_area("אבחנות רפואיות", value=med.get("medicalDiagnoses", ""), disabled=True, height=80)
    
    # -------------- tab 2 - validation results  -----------------------------------------------

    with tab2:

        st.subheader("תוצאות אימות")
        
        validation = results.get("validation", {})
        
        # --- status  ------------------------

        if validation.get("is_valid", False):
            st.success("הטופס עבר אימות בהצלחה")
        else:
            st.warning("נמצאו בעיות באימות הטופס")
        
        # --- metrics ------------------------

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("שלמות הטופס", f"{validation.get('completeness_score', 0):.1%}")

        with col2:
            total = validation.get('summary', {}).get('total_fields', 0)
            filled = validation.get('summary', {}).get('filled_fields', 0)
            st.metric("שדות שמולאו", f"{filled}/{total}")

        with col3:
            missing = len(validation.get('summary', {}).get('missing_required_fields', []))
            st.metric("שדות חובה חסרים", missing)
        
        # --- section metrics ------------------------
        
        if validation.get("section_metrics"):
            st.subheader("מילוי לפי סעיפים")
            
            col1, col2 = st.columns(2)
            
            section_data = validation["section_metrics"]
            sections_list = list(section_data.items())
            
            # ------- Sections 1-3 ----------------------------------

            with col1:
                for i in range(3):
                    if i < len(sections_list):
                        section_name, (filled, total) = sections_list[i]
                        
                        if i == 3:
                            st.metric(f"**{section_name} (קריטי)**", f"{filled}/{total}", 
                                    delta="חובה למילוי" if filled < total else "הושלם")
                        else:
                            st.metric(section_name, f"{filled}/{total}")
            
            # ------- Sections 4-6 ----------------------------------
            
            with col2:
                for i in range(3, 6):
                    if i < len(sections_list):
                        section_name, (filled, total) = sections_list[i]
                        
                        if section_name == "פרטי התאונה":
                            if filled < total:
                                st.metric(f"**{section_name} **", f"{filled}/{total}", 
                                        delta="סעיף קריטי - חסר מידע")
                            else:
                                st.metric(f"**{section_name} **", f"{filled}/{total}", 
                                        delta="סעיף קריטי - הושלם")
                        else:
                            st.metric(section_name, f"{filled}/{total}")
            
            
        # --- errors  ------------------------

        if validation.get("validation_errors"):
            st.error("שגיאות אימות:")
            for error in validation["validation_errors"]:
                st.write(f"• {error}")
        
        # --- fields  ------------------------

        if validation.get("field_level_validation"):
            st.subheader("אימות ברמת השדה")
            invalid_fields = {
                field: details for field, details in validation["field_level_validation"].items()
                if not details.get("is_valid", True)
            }
            if invalid_fields:
                for field, details in invalid_fields.items():
                    st.warning(f"**{field}**: {details.get('error', 'Invalid')}")
    
    # -------------- tab 3 - confidence scores  -----------------------------------------------

    with tab3:
        st.subheader("מטריקות ביצועים")
        
        # --- confidence  ------------------------

        if validation.get("confidence_scores"):

            st.markdown("### ציוני ביטחון")
            
            confidence_data = pd.DataFrame  (
                                                list(validation["confidence_scores"].items()),
                                                columns=["Field", "Confidence"]
                                            )
            confidence_data = confidence_data.sort_values("Confidence", ascending=False)
            
            st.bar_chart(confidence_data.set_index("Field"))
            st.dataframe(
                            confidence_data.style.format({"Confidence": "{:.2f}"}),
                            hide_index=True
                        )
        
        # --- section completion chart  ------------------------
        
        if validation.get("section_metrics"):
            
            # --------- regular sections to complete -------------------------------------
            
            st.markdown("### השלמת סעיפים")
            
            section_data = []
            for section_name, (filled, total) in validation["section_metrics"].items():
                completion_rate = (filled / total * 100) if total > 0 else 0
                section_data.append({
                    "סעיף": section_name,
                    "אחוז השלמה": completion_rate,
                    "מולא": filled,
                    "סה״כ": total
                })
            
            section_df = pd.DataFrame(section_data)
            
            # --------- critical section to complete -------------------------------------

            def highlight_critical(row):
                if row["סעיף"] == "פרטי התאונה":
                    return ['background-color: #ffcccc' if row["אחוז השלמה"] < 100 else 'background-color: #ccffcc'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                section_df.style.apply(highlight_critical, axis=1).format({"אחוז השלמה": "{:.1f}%"}),
                hide_index=True
            )
            
            st.bar_chart(section_df.set_index("סעיף")["אחוז השלמה"])
        
        # --- statistics  ------------------------

        st.markdown("### סטטיסטיקות עיבוד")
        st.write(f"גודל טקסט OCR: {results.get('ocr_text_length', 0)} תווים")
        st.write(f"זמן עיבוד: {datetime.now().isoformat()}")
    
    # -------------- tab 4 - raw json  -----------------------------------------------

    with tab4:

        st.subheader("פלט JSON")
        
        json_output = json.dumps(results["extracted_data"], ensure_ascii=False, indent=2)
        st.code(json_output, language="json")
        
        # Download button
        st.download_button(
            label="הורד JSON",
            data=json_output,
            file_name=f"extracted_data_{results['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


# ------------- main ----------------------------------------------

def main():
    
    logger.info("Application started")

    # --- page configuration ----------------------------------------

    st.set_page_config(
        page_title="מערכת חילוץ טפסים",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
        <style>
        html, body {
             direction: rtl;
        }
    """, unsafe_allow_html=True)

    # --- headline --------------------------------------------------

    st.title("מערכת חילוץ טפסים - ביטוח לאומי")
    st.markdown("מערכת לחילוץ אוטומטי של מידע מטפסי ביטוח לאומי באמצעות AI")
    st.header("העלאת מסמך")

    st.markdown("</div>", unsafe_allow_html=True)  
    
    # --- uploader --------------------------------------------------

    uploaded_file = st.file_uploader(
        "בחר קובץ (PDF, JPG, JPEG, PNG)",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        help="גרור קובץ או לחץ לבחירה"
    )

    # --- process ---------------------------------------------------

    if uploaded_file is not None:

        logger.info(f"File uploaded: {uploaded_file.name} ({uploaded_file.type}, {uploaded_file.size} bytes)")
        
        # --- file metadata ---------------------------------

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("שם קובץ", uploaded_file.name)
        with col2:
            st.metric("סוג קובץ", uploaded_file.type)
        with col3:
            st.metric("גודל", f"{uploaded_file.size / 1024:.1f} KB")
        
        # --- file preview ----------------------------------

        if uploaded_file.type.startswith('image'):

            logger.info(f"Processing initiated by user for file: {uploaded_file.name}")
            
            st.subheader("תצוגה מקדימה")
            image = Image.open(uploaded_file)
            st.image(image, caption=uploaded_file.name, use_column_width=True)
            uploaded_file.seek(0)  
        
        # --- process button ---------------------------------

        if st.button("התחל עיבוד", type="primary", use_container_width=True):
            
            # --- read file -------------------------

            file_content = uploaded_file.read()
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            # --- process file ----------------------

            results = process(file_content, file_type, uploaded_file.name)
            
            # --- store results ----------------------

            st.session_state['last_results'] = results
            
            # --- display results ----------------------

            display(results)
            
            with st.expander("מידע נוסף"):

                st.json(results)

    # --- last results ----------------------------------------------
    
    elif 'last_results' in st.session_state:
        st.info("מציג תוצאות אחרונות")
        display(st.session_state['last_results'])
    
    # --- footer ----------------------------------------------------
    
    st.markdown("---")
   
if __name__ == "__main__":
    main()