import streamlit as st
import pandas as pd
from google.cloud import translate_v3 as translate
from openai import OpenAI
import os
from config import OPENAI_API_KEY, PARENT

# Setup code
client = OpenAI(api_key=OPENAI_API_KEY)
translate_client = translate.TranslationServiceClient()

# Default prompts
DEFAULT_PROMPT = """You are an expert translator proficient in Gujarati, English, and Jain philosophy.
**Task:**
Refine the provided English translation to make it natural, fluent, and coherent.

**Source of Input:**
- The input text is an English translation generated by the Google Translate V3 API from a section of one of the Jain Aagam Shastras books originally written in Gujarati.

**Instructions:**
1. **Tone:** 
- Maintain a formal and professional tone suitable for academic or business audiences.
2. **Reading Level:** 
- Ensure the output is at a college graduate reading level, assuming the reader has some background knowledge of Jain philosophy.
3. **Refinement:**
- Apply a moderate level of refinement by improving grammar and syntax.
- Suggest alternative phrases and sentences where necessary to enhance clarity and flow.
4. **Style Consistency:** 
- Ensure the translation adheres to the AP Stylebook guidelines.
5. **Constraints:**
- **Do Not:** Change the length or alter the exact meaning of the text.
- **Ambiguities:** If any ambiguities are present, make an educated guess while staying true to the original meaning.

**Input Text:**"""

SIMPLE_PROMPT = """Key Requirements:
1. Maintain formal tone
2. Preserve meaning
3. Enhance clarity
4. Keep same length
5. Use Jain terminology

Input text:"""

@st.cache_data(ttl=3600)
def translate_text_v3(text, target_language="en"):
    """Google Translate API call"""
    response = translate_client.translate_text(
        contents=[text],
        target_language_code=target_language,
        parent=PARENT,
        mime_type="text/plain"
    )
    return response.translations[0].translated_text

def refine_with_gpt(text, prompt=""):
    """GPT refinement call"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert specializing in Jain philosophical texts."},
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"GPT refinement error: {str(e)}")
        return text

def initialize_session_state():
    """Initialize session state with defaults"""
    if 'word_pairs_df' not in st.session_state:
        st.session_state.word_pairs_df = pd.DataFrame({
            'google_english': ['aahar', 'dharma', 'karma'],
            'custom_english': ['food', 'religion', 'action'],
            'context': ['dietary context', 'spiritual context', 'philosophical context']
        })
    if 'show_dictionary' not in st.session_state:
        st.session_state.show_dictionary = False

def apply_word_replacements(text):
    """Apply dictionary word replacements"""
    if not text:
        return text
    
    words = text.split()
    replaced_words = []
    
    for word in words:
        match = st.session_state.word_pairs_df[
            st.session_state.word_pairs_df['google_english'].str.lower() == word.lower()
        ]
        
        if not match.empty:
            replaced_words.append(match.iloc[0]['custom_english'])
        else:
            replaced_words.append(word)
    
    return ' '.join(replaced_words)

def main():
    st.set_page_config(
        page_title="Aagam Translation Tool",
        page_icon="📚",
        layout="wide"
    )
    
    initialize_session_state()
    
    st.title("Aagam Shastra - Gujarati to English Translation Tool")
    
    # Main translation interface
    col1, col2, col3 = st.columns(3)
    
    # Column 1: Gujarati Input
    with col1:
        st.subheader("Gujarati Input")
        gujarati_text = st.text_area(
            "Enter Gujarati text here...",
            height=200,
            key="gujarati_input"
        )
        
        if st.button("🌐 Translate", type="primary"):
            if gujarati_text:
                with st.spinner("Translating..."):
                    translated = translate_text_v3(gujarati_text)
                    st.session_state['google_translation'] = translated
            else:
                st.warning("Please enter text to translate")
    
    # Column 2: Google Translation
    with col2:
        st.subheader("Google Translation")
        google_translated = st.text_area(
            "Google translated text will appear here...",
            value=st.session_state.get('google_translation', ''),
            height=200,
            key="google_output"
        )
        
        # Initialize states for toggles if not exists
        if 'use_default_prompt' not in st.session_state:
            st.session_state.use_default_prompt = True
        if 'use_custom_instructions' not in st.session_state:
            st.session_state.use_custom_instructions = False
        if 'use_new_prompt' not in st.session_state:
            st.session_state.use_new_prompt = False
        
        # Action buttons side by side (full width)
        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("🔄 Apply Word Replacements", use_container_width=True):
                if google_translated:
                    with st.spinner("Applying replacements..."):
                        replaced_text = apply_word_replacements(google_translated)
                        st.session_state['google_translation'] = replaced_text
        
        with button_col2:
            if st.button("✨ Refine", use_container_width=True):
                if google_translated:
                    with st.spinner("Refining translation..."):
                        # Build prompt based on active toggles
                        base_prompt = DEFAULT_PROMPT if st.session_state.use_default_prompt else st.session_state.get('new_prompt_value', SIMPLE_PROMPT)
                        additional = st.session_state.get('additional_instructions_value', '') if st.session_state.use_custom_instructions else ""
                        
                        final_prompt = base_prompt
                        if additional:
                            final_prompt = f"{base_prompt}\n\nAdditional Instructions:\n{additional}"
                        
                        refined = refine_with_gpt(google_translated, final_prompt)
                        st.session_state['final_translation'] = refined
        
        # Prompt Configuration Controls
        st.markdown("### Configure Prompt")
        st.markdown("Select the components to use in your prompt:")
        
        # Radio for base prompt selection
        prompt_base = st.radio(
            "Base Prompt:",
            options=["Default Prompt", "New Custom Prompt"],
            horizontal=True,
            key="prompt_base_radio"
        )
        st.session_state.use_default_prompt = prompt_base == "Default Prompt"
        st.session_state.use_new_prompt = prompt_base == "New Custom Prompt"
        
        # Custom instructions toggle
        st.session_state.use_custom_instructions = st.toggle(
            "Add Custom Instructions",
            value=st.session_state.use_custom_instructions,
            help="Toggle to add additional instructions to your base prompt"
        )
        
        # Current prompt preview
        st.markdown("#### Current Configuration Preview:")
        base = "Default Prompt" if st.session_state.use_default_prompt else "New Custom Prompt"
        instructions = "with Custom Instructions" if st.session_state.use_custom_instructions else "without Custom Instructions"
        st.info(f"Using {base} {instructions}")
        
        # Prompt Management Section
        st.markdown("### Manage Prompts")
        
        # Tab-based interface for prompt management
        prompt_tabs = st.tabs(["📜 Default Prompt", "✏️ New Prompt", "➕ Custom Instructions"])
        
        with prompt_tabs[0]:
            st.markdown("**Current Default Prompt:**")
            st.markdown(f"```\n{DEFAULT_PROMPT}\n```")
        
        with prompt_tabs[1]:
            if 'new_prompt_value' not in st.session_state:
                st.session_state.new_prompt_value = SIMPLE_PROMPT
                
            new_prompt = st.text_area(
                "Create a new base prompt",
                value=st.session_state.new_prompt_value,
                height=200,
                key="new_prompt",
                placeholder=SIMPLE_PROMPT,
                help="Replace the entire default prompt with your custom version"
            )
            
            if st.button("Apply New Prompt", use_container_width=True):
                st.session_state.new_prompt_value = new_prompt
                st.success("New prompt saved! Make sure 'New Custom Prompt' is selected above to use it.")
        
        with prompt_tabs[2]:
            if 'additional_instructions_value' not in st.session_state:
                st.session_state.additional_instructions_value = ''
            
            additional_instructions = st.text_area(
                "Add custom instructions",
                value=st.session_state.additional_instructions_value,
                height=150,
                key="additional_instructions",
                help="These instructions will be added to your selected base prompt"
            )
            
            if st.button("Apply Custom Instructions", use_container_width=True):
                st.session_state.additional_instructions_value = additional_instructions
                st.success("Custom instructions saved! Make sure 'Add Custom Instructions' is toggled on to use them.")
        
        # Final Preview
        if st.checkbox("Show Full Prompt Preview"):
            st.markdown("### 📋 Full Prompt Preview")
            base = DEFAULT_PROMPT if st.session_state.use_default_prompt else st.session_state.get('new_prompt_value', SIMPLE_PROMPT)
            additional = st.session_state.get('additional_instructions_value', '') if st.session_state.use_custom_instructions else ""
            
            if additional:
                st.markdown("**Base Prompt:**")
                st.code(base)
                st.markdown("**Additional Instructions:**")
                st.code(additional)
            else:
                st.code(base)
    
    # Column 3: Final Translation
    with col3:
        st.subheader("Final Translation")
        st.text_area(
            "GPT refined translation will appear here...",
            value=st.session_state.get('final_translation', ''),
            height=200,
            key="final_output"
        )
    
    # Dictionary interface
    with st.expander("Word Replacement Dictionary"):
        cols = st.columns([1, 2])
        
        with cols[0]:
            st.subheader("Add New Word Pair")
            google_word = st.text_input("Google Translation Word/Phrase")
            custom_word = st.text_input("Custom Translation")
            context = st.text_input("Context (optional)")
            
            if st.button("➕ Add to Dictionary"):
                if google_word and custom_word:
                    new_row = pd.DataFrame({
                        'google_english': [google_word],
                        'custom_english': [custom_word],
                        'context': [context if context else '']
                    })
                    st.session_state.word_pairs_df = pd.concat(
                        [st.session_state.word_pairs_df, new_row],
                        ignore_index=True
                    )
                    st.success("Word pair added!")
        
        with cols[1]:
            st.subheader("Current Dictionary")
            st.text_input("🔍 Search dictionary...")
            st.dataframe(st.session_state.word_pairs_df, hide_index=True)

if __name__ == "__main__":
    main()