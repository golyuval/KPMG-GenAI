import gradio as gr, requests, os, json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Core import config

BACKEND = config.chatbot_server_endpoint
init_state = {"history": [], "user_info": None}

def talk(user_msg, history):
    # Reconstruct full state from chat history
    state = {"history": [], "user_info": None}
    
    # Convert Gradio tuples back to dict format for backend
    for user, assistant in (history or []):
        state["history"].append({"role": "user", "content": user})
        state["history"].append({"role": "assistant", "content": assistant})
    
    payload = {**state, "user_msg": user_msg}
    
    r = requests.post(BACKEND, json=payload, timeout=30)
    data = r.json()

    assistant = data["assistant_msg"]
    
    # Return in Gradio's expected format: list of tuples
    new_history = (history or []) + [(user_msg, assistant)]
    
    return new_history, ""

def main():
    with gr.Blocks(title="KPMG Chatbot Alpha") as demo:
        
        gr.HTML("""
<style>
    /* Text direction and alignment */
    .message.user, .message.assistant {
        direction: rtl;
        text-align: right;
        white-space: pre-line;
    }
    
    /* Header alignment */
    h1 {
        direction: rtl;
        text-align: right;
    }
    
    /* Target the specific classes from the DOM */
    .message-row.bubble.user-row.svelte-1csvgiq,
    .message-row.bubble.bot-row.svelte-1csvgiq {
        justify-content: flex-start !important;
        direction: rtl !important;
    }
    
    /* Target the flex-wrap container */
    .flex-wrap.svelte-1csvgiq {
        justify-content: flex-start !important;
        direction: rtl !important;
    }
    
    /* Target the bot message specifically */
    .bot.svelte-1csvgiq.message {
        margin-left: 0 !important;
        margin-right: auto !important;
    }
    
    /* Target the message content */
    .message-content {
        text-align: right !important;
        direction: rtl !important;
    }
    
    /* Target the message panel */
    .message.svelte-1csvgiq.panel-full-width {
        text-align: right !important;
        direction: rtl !important;
    }
</style>
""")
        gr.Markdown("# צ'אטבוט ביטוח לאומי בשיתוף עם KPMG")

        # Add initial message
        initial_history = [("", "שלום ! אני הצ'אטבוט החדש של ביטוח לאומי 😊\nאני רק צריך כמה פרטים כדי שאדע איך לעזור בצורה הטובה ביותר.\nיש לשלוח הודעה כדי להתחיל את התהליך")]
        chatbot = gr.Chatbot(label="Session", height=500, value=initial_history)
        textbox = gr.Textbox(placeholder="שאל שאלה...", label="שאלה")

        textbox.submit(
            talk,
            inputs=[textbox, chatbot],
            outputs=[chatbot, textbox]
        )

    demo.launch(share=True)

if __name__ == "__main__":
    main()
