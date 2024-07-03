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
    "Luego puedes modificar el contenido generado y pedir más refinamientos."
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

    # Generate content based on the PDFs
    if st.button("Generar Contenido"):
        messages = [
            {
                "role": "system",
                "content": f"Eres un asistente de IA que genera {content_type}(s) basado en el contenido de documentos PDF y tomando inspiración de las siguientes publicaciones de LinkedIn: {inspiration_posts}. Solo retorna el contenido:"
            },
            {
                "role": "user",
                "content": f"Genera una {content_type} basada en el siguiente contenido del documento: {document}. El contenido debe tener aproximadamente {word_count} palabras."
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
                st.session_state.generated_content = generated_content

# Textarea for editing the generated content
if 'generated_content' in st.session_state:
    # User input for refinement request
    st.text_area("Contenido Generado:", value=st.session_state.generated_content, height=300)
    refinement_request = st.text_input("Pidele algo al bot:")

    if st.button("Refinar Contenido"):
        messages = [
            {"role": "system", "content": f"Eres un asistente de IA que ayuda a refinar una {content_type}. Solo retorna el contenido. Manten el contenido unico y no modifiques el tono del contenido."},
            {"role": "user", "content": f"Aquí está el {content_type} actual:\n\n{st.session_state.generated_content}\n\Realiza lo siguiente: {refinement_request}"}
        ]

        # Generate refined content using the OpenAI API with streaming
        stream = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            stream=True
        )

        st.session_state.generated_content = ""
        st.text("Refinando contenido...")
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                st.session_state.generated_content += chunk.choices[0].delta.content

        st.rerun()