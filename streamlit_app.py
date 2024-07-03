import streamlit as st
from openai import OpenAI
import PyPDF2
import io

# Set your OpenAI API key here
OPENAI_API_KEY = ""

# Create an OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

OPENAI_MODEL = "gpt-3.5-turbo"

st.title("📝 Generador de Publicaciones de LinkedIn/Blog")
st.write(
    "Sube un documento PDF y genera una publicación de LinkedIn o un artículo de blog basado en su contenido. "
    "Selecciona un tema de las sugerencias generadas, genera el contenido, y luego puedes refinarlo."
)

# Let the user choose between LinkedIn post or blog article
content_type = st.selectbox(
    "Elige el tipo de contenido a generar",
    options=["Publicación de LinkedIn", "Artículo de Blog"]
)

# Let the user upload a PDF file
uploaded_files = st.file_uploader("Sube documentos PDF", type="pdf", accept_multiple_files=True)

# Input for LinkedIn posts for inspiration
inspiration_posts = st.text_area(
    "Pega 2 o más publicaciones de LinkedIn para tomar inspiración:",
    height=150
)

# Input for desired word count
word_count = st.number_input(
    "Número de palabras deseadas para el contenido generado:",
    min_value=50,
    max_value=3000,
    value=500,
    step=50
)

if uploaded_files:
    # Process the uploaded PDF files
    document = ""
    for uploaded_file in uploaded_files:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
        for page in pdf_reader.pages:
            document += page.extract_text()

    # Generate content suggestions based on the PDFs
    if st.button("Generar Sugerencias de Contenido"):
        messages = [
            {
                "role": "system",
                "content": f"Eres un asistente de IA que genera sugerencias de temas para {content_type}(s) basado en el contenido de documentos PDF y tomando inspiración de las siguientes publicaciones de LinkedIn: {inspiration_posts}. Genera una lista numerada de 5 sugerencias de temas."
            },
            {
                "role": "user",
                "content": f"Genera 5 sugerencias de temas para {content_type} basadas en el siguiente contenido del documento: {document}."
            }
        ]

        # Generate content suggestions using the OpenAI API
        st.write(f"Generando sugerencias de temas para {content_type}...")
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=500
        )
        
        st.session_state.content_suggestions = response.choices[0].message.content.split('\n')
        st.session_state.generated_contents = {}

    # Display content suggestions and let user interact with each
    if 'content_suggestions' in st.session_state:
        for i, suggestion in enumerate(st.session_state.content_suggestions):
            with st.expander(f"{suggestion[:100]}..."):
                st.text(suggestion)
                if f"generated_content_{i}" not in st.session_state.generated_contents:
                    if st.button(f"Generar Contenido", key=f"generate_{i}"):
                        messages = [
                            {
                                "role": "system",
                                "content": f"Eres un asistente de IA que genera {content_type}(s) basado en un tema seleccionado. Solo retorna el contenido:"
                            },
                            {
                                "role": "user",
                                "content": f"Genera una {content_type} basada en el siguiente tema: {suggestion}. El contenido debe tener aproximadamente {word_count} palabras."
                            }
                        ]

                        # Generate content using the OpenAI API with streaming
                        st.write(f"Generando {content_type}...")
                        generated_content = ""
                        stream = client.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=messages,
                            stream=True,
                            max_tokens=word_count * 5  # Approximate token count based on word count
                        )

                        for chunk in stream:
                            if chunk.choices[0].delta.content is not None:
                                generated_content += chunk.choices[0].delta.content
                        
                        st.session_state.generated_contents[f"generated_content_{i}"] = generated_content
                        st.rerun()

                if f"generated_content_{i}" in st.session_state.generated_contents:
                    content = st.session_state.generated_contents[f"generated_content_{i}"]
                    st.text_area(f"Contenido Generado:", value=content, height=300, key=f"content_area_{i}")
                    
                    refinement_request = st.text_input(f"Pidele algo al bot para refinar el contenido:", key=f"refine_input_{i}")
                    if st.button(f"Refinar Contenido", key=f"refine_button_{i}"):
                        messages = [
                            {"role": "system", "content": f"Eres un asistente de IA que ayuda a refinar una {content_type}. Solo retorna el contenido. Manten el contenido unico y no modifiques el tono del contenido."},
                            {"role": "user", "content": f"Aquí está el {content_type} actual:\n\n{content}\n\Realiza lo siguiente: {refinement_request}"}
                        ]

                        # Generate refined content using the OpenAI API with streaming
                        stream = client.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=messages,
                            stream=True
                        )

                        refined_content = ""
                        st.text(f"Refinando contenido de '{suggestion}'...")
                        for chunk in stream:
                            if chunk.choices[0].delta.content is not None:
                                refined_content += chunk.choices[0].delta.content

                        st.session_state.generated_contents[f"generated_content_{i}"] = refined_content
                        st.rerun()

# Option to reset and start over
if 'content_suggestions' in st.session_state:
    if st.button("Reiniciar y Generar Nuevas Sugerencias"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()