import gradio as gr
import requests
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Core import config
from Core.logger_setup import get_logger

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
        
        for user, assistant in (history or []):
            if user:  
                state["history"].append({"role": "user", "content": user})
                state["history"].append({"role": "assistant", "content": assistant})
        

        payload = {
            "history": state["history"],
            "user_info": state["user_info"],
            "user_msg": user_msg.strip()
        }
        
        logger.info(f"Sending request to backend: {user_msg[:50]}...")
        
        # ------ call server ---------------------------------------------

        response = requests.post(config.chatbot_server_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # ------ process response ---------------------------------------------

        if data.get("user_info"):
            user_info_state = data["user_info"]
            logger.info("User info collected successfully")
        
        assistant_msg = data.get("assistant_msg", "מצטער, לא קיבלתי תשובה מהשרת.")
        new_history = (history or []) + [(user_msg, assistant_msg)]
        
        logger.info(f"Successfully received response from backend for user: {user_info_state.get('id_number', 'anonymous') if user_info_state else 'anonymous'}")
        
        return new_history, "", user_info_state
    
    # ------ errors ---------------------------------------------

    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        error_msg = "הבקשה לקחה יותר מדי זמן. אנא נסה שוב."
        new_history = (history or []) + [(user_msg, error_msg)]
        return new_history, "", user_info_state
        
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to backend")
        error_msg = "לא ניתן להתחבר לשרת. אנא וודא שהשרת פועל."
        new_history = (history or []) + [(user_msg, error_msg)]
        return new_history, "", user_info_state
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Backend error: {str(e)}")
        error_msg = "מצטער, יש בעיה בחיבור לשרת. אנא נסה שוב."
        new_history = (history or []) + [(user_msg, error_msg)]
        return new_history, "", user_info_state
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        error_msg = "אירעה שגיאה לא צפויה. אנא נסה שוב."
        new_history = (history or []) + [(user_msg, error_msg)]
        return new_history, "", user_info_state

# ------------- main ui ---------------------------------------------

def main():
    css = """
    /* Default RTL layout for the entire app */
    html, body, .gradio-container { direction: rtl; }

    /* Center only the header and subheader */
    #app-header, #app-subheader { text-align: center; }

    /* Phase indicator */
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

    /* Align footer and examples text to the right */
    .footer { direction: rtl; text-align: right; }
    """

    with gr.Blocks(title="KPMG Chatbot Alpha",
                   theme=gr.themes.Soft(),
                   css=css) as demo:

        # ---------- Header --------------------------------------------------

        gr.Markdown("# צ'אטבוט ביטוח בריאות - KPMG", elem_id="app-header")
        gr.Markdown("### מערכת חכמה למתן מידע על שירותי בריאות בקופות החולים",
                    elem_id="app-subheader")

        # ---------- State ---------------------------------------------------

        user_info_state = gr.State(None)

        # ---------- Phase Indicator -----------------------------------------

        phase_indicator = gr.HTML(
            value='<div class="phase-indicator collection-phase">'
                  'שלב 1: איסוף פרטים אישיים</div>'
        )

        # ---------- Chatbot -------------------------------------------------
        
        initial_history = [(
                "",
                "שלום! 👋 אני העוזר הדיגיטלי שלך לשירותי ביטוח בריאות.\n"
                "כדי שאוכל לתת לך מידע מדויק על הזכויות שלך, אני צריך לאסוף כמה פרטים.\n"
                "בוא נתחיל, מה שמך הפרטי?"
            )]
        
        chatbot = gr.Chatbot(
            label="שיחה",
            height=500,
            value=initial_history,
            bubble_full_width=False,
            rtl=True
        )

        # ---------- Input Section -------------------------------------------

        with gr.Row():
            textbox = gr.Textbox(
                placeholder="הקלד את הודעתך כאן…",
                label="הודעה",
                lines=1,            # ⇨ pressing Enter submits
                scale=4,
                autofocus=True,
                rtl=True
            )
            submit_btn = gr.Button("שלח", variant="primary")

        # ---------- Submit Callback -----------------------------------------

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

        # ---------- Footer --------------------------------------------------
        
        gr.HTML("""
        <div class="footer">
            <p><strong>טיפ:</strong> המערכת תומכת בעברית ובאנגלית. תוכל לשאול בכל שפה שנוחה לך!</p>
            <p>כל המידע שלך מאובטח ולא נשמר לאחר סיום השיחה.</p>
        </div>
        """)

    demo.launch(share=True, server_name="0.0.0.0", server_port=7860)

# ------------- entry point -----------------------------------------

if __name__ == "__main__":
    main()