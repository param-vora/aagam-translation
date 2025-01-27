import streamlit as st
import pandas as pd
import json
from google.cloud import translate_v3 as translate
import openai
import os
from config import OPENAI_API_KEY, PARENT

# Initialize clients
client = openai.OpenAI(api_key=OPENAI_API_KEY)
translate_client = translate.TranslationServiceClient()

DEFAULT_PROMPT = """You are a super high-level Jain theology expert specializing in translation refinement.
Your task is to:
1. If the input is in English:
   - If it appears to be feedback on a previous translation, incorporate that feedback to improve the translation
   - If it appears to be new text, refine it while preserving theological accuracy
2. If the input is in Gujarati with a basic translation:
   - Refine the translation while preserving theological accuracy
   - Consider cultural and religious context

Return results in JSON format:
{
    "final_translation": "refined translation here",
    "uncertainties": [
        {
            "segment": "specific text",
            "reason": "explanation of uncertainty",
            "suggested_followup": "specific question to resolve this uncertainty"
        }
    ]
}
Custom Instructions: 
"""

def init_session():
    """Initialize session state variables"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "word_pairs_df" not in st.session_state:
        st.session_state.word_pairs_df = pd.DataFrame({
            'google_english': ['aahar', 'dharma', 'karma'],
            'custom_english': ['food', 'religion', 'action'],
            'context': ['dietary context', 'spiritual context', 'philosophical context']
        })
    if "current_source_text" not in st.session_state:
        st.session_state.current_source_text = ""
    if "uncertainties" not in st.session_state:
        st.session_state.uncertainties = []
    if "pending_followups" not in st.session_state:
        st.session_state.pending_followups = []
    if "chat_input" not in st.session_state:
        st.session_state.chat_input = ""
    # Initialize prompt-related state
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = DEFAULT_PROMPT

def reset_chat_session():
    """Reset chat-related session state"""
    st.session_state.chat_history = []
    st.session_state.uncertainties = []
    st.session_state.pending_followups = []
    st.session_state.current_source_text = ""
    st.session_state.chat_input = ""

def update_system_prompt():
    """Update the system prompt when the text area changes"""
    print(f"Attempting to update prompt to: {st.session_state.prompt_editor}")
    st.session_state.system_prompt = st.session_state.prompt_editor
    print(f"System prompt updated to: {st.session_state.system_prompt}")

def apply_dictionary_replacements(text):
    """Apply word replacements from dictionary"""
    if not text:
        return text
    
    words = text.split()
    replaced = []
    for word in words:
        row = st.session_state.word_pairs_df[
            st.session_state.word_pairs_df['google_english'].str.lower() == word.lower()
        ]
        if not row.empty:
            replaced.append(row.iloc[0]['custom_english'])
        else:
            replaced.append(word)
    return ' '.join(replaced)

def gpt_chat_call(prompt, context=""):
    """Enhanced GPT call with context handling"""
    try:
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nInput:\n{prompt}"
        
        # Debug print to verify the prompt being used
        print(f"Using prompt in GPT call: {st.session_state.system_prompt}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": st.session_state.system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1
        )
        result = response.choices[0].message.content.strip()
        
        try:
            parsed = json.loads(result)
            translation = parsed.get("final_translation", result)
            translation = apply_dictionary_replacements(translation)
            return translation, parsed.get("uncertainties", [])
        except json.JSONDecodeError:
            return result, []
            
    except Exception as e:
        st.error(f"GPT error: {str(e)}")
        return None, []

def translate_text_v3(text, target_language="en"):
    """Google Translate with dictionary replacements"""
    try:
        response = translate_client.translate_text(
            contents=[text],
            target_language_code=target_language,
            parent=PARENT,
            mime_type="text/plain"
        )
        translation = response.translations[0].translated_text
        return apply_dictionary_replacements(translation)
    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="Jain Translation Assistant", layout="wide")
    
    st.markdown("""
    <style>
    .main {
        background-color: #FAFAFA;
    }
    .user-bubble {
        background-color: #D2F8C6;
        padding: 10px;
        border-radius: 10px;
        margin-left: 20%;
        margin-bottom: 10px;
        color: #333;
    }
    .assistant-bubble {
        background-color: #ECECEC;
        padding: 10px;
        border-radius: 10px;
        margin-right: 20%;
        margin-bottom: 10px;
        color: #333;
    }
    .stButton>button {
        background-color: #2A7BEF !important;
        color: #FFFFFF !important;
        border-radius: 5px !important;
    }
    .css-1p05t8e, .css-18e3th9, .css-h5rgaw {
        padding-top: 1rem;
    }
    .stDataFrame table {
        background-color: #FFFFFF;
    }
    html, body, [class*="css"] {
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    init_session()
    
    st.title("Translation Dashboard")
    st.write(
        "Use this tool to refine Gujarati-to-English translations. You can do a quick word-to-word translation, "
        "request a more refined translation, or have a chat-based interaction to further refine or discuss."
    )

    input_col, button_col, chat_col = st.columns([4, 1, 5], gap="large")
    
    with input_col:
        st.subheader("Gujarati Input")
        gujarati_input = st.text_area(
            "Source Text",
            label_visibility="visible",
            placeholder="Enter Gujarati text here...",
            height=250
        )
        
        if st.button("Start New Translation"):
            reset_chat_session()
            st.rerun()
            
        # Add prompt editor in an expander
        with st.expander("Prompt Editor", expanded=False):
            st.text_area(
                "System Prompt",
                value=st.session_state.system_prompt,
                key="prompt_editor",
                height=400,
                on_change=update_system_prompt
            )
            
            if st.button("Reset to Default Prompt"):
                st.session_state.system_prompt = DEFAULT_PROMPT
                st.rerun()
    
    with button_col:
        st.subheader("Actions")
        
        if st.button("Word-to-Word Translation"):
            if gujarati_input.strip():
                if gujarati_input != st.session_state.current_source_text:
                    reset_chat_session()
                    st.session_state.current_source_text = gujarati_input
                with st.spinner("Translating..."):
                    translation = translate_text_v3(gujarati_input)
                    if translation:
                        st.session_state.chat_history = [
                            {"role": "user", "content": "Source text:\n" + gujarati_input},
                            {"role": "assistant", "content": "Word-to-word translation:\n" + translation}
                        ]
                        st.rerun()
            else:
                st.warning("Please enter Gujarati text.")
        
        if st.button("Refined Translation"):
            if gujarati_input.strip():
                if gujarati_input != st.session_state.current_source_text:
                    reset_chat_session()
                    st.session_state.current_source_text = gujarati_input
                with st.spinner("Processing..."):
                    base_translation = translate_text_v3(gujarati_input)
                    if base_translation:
                        prompt = f"Original Gujarati:\n{gujarati_input}\nBasic Translation:\n{base_translation}"
                        refined, uncertainties = gpt_chat_call(prompt)
                        if refined:
                            st.session_state.chat_history = [
                                {"role": "user", "content": "Source text:\n" + gujarati_input},
                                {"role": "assistant", "content": "Refined translation:\n" + refined}
                            ]
                            st.session_state.uncertainties = uncertainties
                            if uncertainties:
                                st.session_state.pending_followups = [
                                    u["suggested_followup"] for u in uncertainties
                                ]
                            st.rerun()
            else:
                st.warning("Please enter Gujarati text.")
    
    with chat_col:
        st.subheader("Translation Refinement Chat")
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='user-bubble'><b>You:</b><br>{msg['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='assistant-bubble'><b>Assistant:</b><br>{msg['content']}</div>",
                    unsafe_allow_html=True
                )
        
        if st.session_state.uncertainties:
            with st.expander("Translation Uncertainties", expanded=True):
                for idx, uncertainty in enumerate(st.session_state.uncertainties):
                    st.warning(f"""
**Uncertain Segment:** {uncertainty['segment']}\n
**Reason:** {uncertainty['reason']}\n
**Suggested Question:** {uncertainty['suggested_followup']}
""")
        
        # Chat input and send button
        if "chat_input" not in st.session_state:
            st.session_state.chat_input = ""

        chat_input = st.text_area(
            "Chat Input",
            placeholder="Discuss or refine the translation...",
            height=100,
            key="chat_input"
        )
        
        if st.button("Send"):
            if chat_input.strip():  # Use the local variable instead of session state
                st.session_state.chat_history.append({"role": "user", "content": chat_input})
                
                with st.spinner("Processing..."):
                    context = f"Original source text: {st.session_state.current_source_text}\n"
                    if len(st.session_state.chat_history) > 1:
                        context += "Previous translation: " + st.session_state.chat_history[1]["content"]
                    
                    response, new_uncertainties = gpt_chat_call(chat_input, context)
                    if response:
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        st.session_state.uncertainties = new_uncertainties
                        if new_uncertainties:
                            st.session_state.pending_followups = [
                                u["suggested_followup"] for u in new_uncertainties
                            ]
                
                st.rerun()
        
        with st.expander("Word Replacement Dictionary"):
            st.write(
                "Add or modify words in the custom dictionary so the tool can replace "
                "default Google translations with your own preferred translations."
            )
            dict_cols = st.columns(3)
            with dict_cols[0]:
                google_word = st.text_input("Google Translation")
            with dict_cols[1]:
                custom_word = st.text_input("Preferred Translation")
            with dict_cols[2]:
                context_text = st.text_input("Usage Context")
            
            if st.button("Add to Dictionary"):
                if google_word and custom_word:
                    new_row = pd.DataFrame({
                        'google_english': [google_word],
                        'custom_english': [custom_word],
                        'context': [context_text or '']
                    })
                    st.session_state.word_pairs_df = pd.concat(
                        [st.session_state.word_pairs_df, new_row],
                        ignore_index=True
                    )
                    st.success("Added to dictionary!")
            
            st.dataframe(st.session_state.word_pairs_df, hide_index=True)

if __name__ == "__main__":
    main()