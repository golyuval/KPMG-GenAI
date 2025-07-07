from pathlib import Path
import gradio as gr
import requests
import os
import sys
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from Core.logger import get_logger
from config import chatbot_server_endpoint

# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

# ------------- chat handler ----------------------------------------

def talk(user_msg, history, user_info_state):
    
    try:

        # ------ input validation (can be enhanced) --------------------------

        if not user_msg or not user_msg.strip():
            return history, "", user_info_state
        
        # ------ prepare payload ---------------------------------------------

        state = {"history": [], "user_info": user_info_state}
        for msg in (history or []):
            if msg["role"] == "user":
                state["history"].append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                state["history"].append({"role": "assistant", "content": msg["content"]})

        # Ensure user_info is not None
        if state["user_info"] is None:
            state["user_info"] = {"verified": False, "collection_complete": False}

        payload = {
            "history": state["history"],
            "user_info": state["user_info"],
            "user_msg": user_msg.strip()
        }
        
        logger.info(f"Sending request to backend: {user_msg[:50]}...")
        logger.info(f"DEBUG CLIENT: Sending user_info_state: {user_info_state}")
        response = requests.post(chatbot_server_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # ------ process response ---------------------------------------------

        if data.get("user_info"):
            user_info_state = data["user_info"]
            logger.info("User info collected successfully")
            logger.info(f"DEBUG CLIENT: Received user_info: {user_info_state}")
        else:
            logger.info("DEBUG CLIENT: No user_info in response")

        assistant_msg = data.get("assistant_msg", "מצטער, לא קיבלתי תשובה מהשרת.")
        new_history = (history or []) + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg}
        ]
        logger.info(f"Successfully received response from backend for user: {user_info_state.get('id_number', 'anonymous') if user_info_state else 'anonymous'}")
        return new_history, "", user_info_state
    
    # ------ errors ---------------------------------------------

    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        error_msg = "הבקשה לקחה יותר מדי זמן. אנא נסה שוב."
        new_history = (history or []) + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": error_msg}
        ]
        return new_history, "", user_info_state
    
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to backend")
        error_msg = "לא ניתן להתחבר לשרת. אנא וודא שהשרת פועל."
        new_history = (history or []) + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": error_msg}
        ]
        return new_history, "", user_info_state
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Backend error: {str(e)}")
        error_msg = "מצטער, יש בעיה בחיבור לשרת. אנא נסה שוב."
        new_history = (history or []) + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": error_msg}
        ]
        return new_history, "", user_info_state
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        error_msg = "אירעה שגיאה לא צפויה. אנא נסה שוב."
        new_history = (history or []) + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": error_msg}
        ]
        return new_history, "", user_info_state

# ------------- main ui ---------------------------------------------

def main():

    css = """

    html, body, .gradio-container { direction: rtl; }

    #app-header, #app-subheader { text-align: center; }
    
    .phase-indicator {
        text-align: center;
        padding: 12px;
        margin: 10px 0;
        border-radius: 8px;
        font-weight: bold;
        font-family: 'Segoe UI', Arial, sans-serif;
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .footer { 
     direction: rtl; 
     text-align: right; }
    """

    with gr.Blocks(title="KPMG Chatbot Alpha",
                   theme=gr.themes.Soft(),
                   css=css) as demo:

        
        # ---------- State Section ---------------------------------------------------

        user_info_state = gr.State({"verified": False, "collection_complete": False})
        session_id = gr.State("")

        # ---------- UI Section ------------------------------------------------------


        # ---- Header -------------------------

        gr.Markdown("# צ'אטבוט ביטוח בריאות - KPMG", elem_id="app-header")
        gr.Markdown("### מערכת חכמה למתן מידע על שירותי בריאות בקופות החולים", elem_id="app-subheader")

        # ---- Phase Indicator ----------------

        phase_indicator = gr.HTML(
            value='<div class="phase-indicator collection-phase">'
                  'שלב 1: איסוף פרטים אישיים</div>'
        )

        # ---- Chat ---------------------------
        
        initial_history = [
            {"role": "assistant", "content": "שלום! 👋 אני העוזר הדיגיטלי שלך לשירותי ביטוח בריאות.\nכדי שאוכל לתת לך מידע מדויק על הזכויות שלך, אני צריך לאסוף כמה פרטים.\nבוא נתחיל, מה שמך הפרטי?"}
        ]

        chatbot = gr.Chatbot(
            label="שיחה",
            height=500,
            value=initial_history,
            rtl=True,
            type="messages"
        )

        # ---- Submit -------------------------

        with gr.Row():
            textbox = gr.Textbox(
                placeholder="הקלד את הודעתך כאן…",
                label="הודעה",
                lines=1,            
                scale=4,
                autofocus=True,
                rtl=True
            )
            submit_btn = gr.Button("שלח", variant="primary")

        # ---- Footer -------------------------

        gr.HTML("""
        <div class="footer">
            <p><strong>טיפ:</strong> המערכת תומכת בעברית ובאנגלית. תוכל לשאול בכל שפה שנוחה לך!</p>
            <p>כל המידע שלך מאובטח ולא נשמר לאחר סיום השיחה.</p>
        </div>
        """)


        # ---------- Callbacks Section -----------------------------------------

        def on_submit(user_msg, history, info):
            new_hist, _, new_info = talk(user_msg, history, info)
            phase_html = (
                '<div class="phase-indicator">מענה על שאלות</div>' if
                new_info and new_info.get("verified") else
                '<div class="phase-indicator">אימות פרטים</div>'
                if new_info else
                '<div class="phase-indicator">איסוף פרטים אישיים</div>'
            )
            return new_hist, "", new_info, phase_html

        submit_btn.click(on_submit,
                         [textbox, chatbot, user_info_state],
                         [chatbot, textbox, user_info_state, phase_indicator])

        textbox.submit(on_submit,
                       [textbox, chatbot, user_info_state],
                       [chatbot, textbox, user_info_state, phase_indicator])


    demo.launch(share=True, server_name="0.0.0.0", server_port=7860)

# ------------- entry point -----------------------------------------

if __name__ == "__main__":
    main()