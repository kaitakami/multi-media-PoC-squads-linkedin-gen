import streamlit as st
import PyPDF2
import io
from openai import OpenAI
import os
from deepgram import DeepgramClient, DeepgramClientOptions, PrerecordedOptions, FileSource
import httpx
from pytube import YouTube
import tempfile
import uuid
import requests

# Create an OpenAI client


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create a Deepgram client
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

OPENAI_MODEL = "gpt-4o"

st.title("📝 SquadS Ventures PoC Generador de Publicaciones de LinkedIn/Blog")
st.write(
    "Sube un documento PDF, pega un enlace de YouTube, ingresa URLs de sitios web o genera contenido basado en texto. "
    "Selecciona un tema de las sugerencias generadas, genera el contenido, y luego puedes refinarlo. Puedes hacerlo con todas las sugerencias!"
)

# Function to download YouTube audio
def download_youtube_audio(url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        # Create a unique filename using UUID
        unique_filename = f"{uuid.uuid4().hex}.mp4"
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, unique_filename)
        
        audio_stream.download(output_path=temp_dir, filename=unique_filename)
        return file_path
    except Exception as e:
        st.error(f"Error al descargar el audio de YouTube: {str(e)}")
        return None

# Function to transcribe audio using Deepgram
def transcribe_audio(file_path):
    with open(file_path, "rb") as file:
        buffer_data = file.read()
    
    payload = {"buffer": buffer_data}
    options = PrerecordedOptions(
        model="nova-2",
        smart_format=True,
        utterances=True,
        punctuate=True,
        diarize=True,
    )
    
    response = deepgram.listen.prerecorded.v("1").transcribe_file(
        payload, options, timeout=httpx.Timeout(300.0, connect=10.0)
    )
    
    return response.results.channels[0].alternatives[0].transcript

# Function to fetch web content using Jina reader
def fetch_web_content(url):
    jina_url = f"https://r.jina.ai/{url}"
    response = requests.get(jina_url)
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Error al obtener el contenido de {url}: {response.status_code}")
        return None

# Let the user choose between LinkedIn post or blog article
content_type = st.selectbox(
    "Elige el tipo de contenido a generar",
    options=["Publicación de LinkedIn", "Artículo de Blog"]
)

# Let the user choose the input type
input_type = st.radio(
    "Elige el tipo de entrada:",
    options=["Documento PDF", "Enlace de YouTube", "URLs de sitios web", "Texto"]
)

if input_type == "Documento PDF":
    uploaded_files = st.file_uploader("Sube documentos PDF", type="pdf", accept_multiple_files=True)
elif input_type == "Enlace de YouTube":
    youtube_url = st.text_input("Pega el enlace de YouTube:")
elif input_type == "URLs de sitios web":
    web_urls = st.text_area("Ingresa hasta 3 URLs de sitios web (una por línea):")
else:
    text_input = st.text_area("Ingresa el texto:")

# Input for LinkedIn posts for inspiration
inspiration_posts = st.text_area(
    "Pega 2 o más publicaciones de LinkedIn para tomar inspiración:",
    height=150
)

st.session_state.suggestions_num = st.slider("El número de sugerencias de contenido que quieres", 5, 25, 10)

# Input for desired word count
word_count = st.number_input(
    "Número de palabras deseadas para el contenido generado:",
    min_value=50,
    max_value=3000,
    value=500,
    step=50
)

if st.button("Generar Sugerencias de Contenido"):
    document = ""
    if input_type == "Documento PDF" and uploaded_files:
        for uploaded_file in uploaded_files:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            for page in pdf_reader.pages:
                document += page.extract_text()
    elif input_type == "Enlace de YouTube" and youtube_url:
        with st.spinner("Descargando y transcribiendo el audio del video..."):
            audio_file = download_youtube_audio(youtube_url)
            if audio_file:
                document = transcribe_audio(audio_file)
                os.remove(audio_file)  # Clean up the temporary file
            else:
                st.error("No se pudo procesar el video de YouTube.")
    elif input_type == "URLs de sitios web" and web_urls:
        urls = web_urls.strip().split('\n')[:3]  # Limit to 3 URLs
        with st.spinner("Obteniendo contenido de los sitios web..."):
            for url in urls:
                content = fetch_web_content(url.strip())
                if content:
                    document += f"\n\nContenido de {url}:\n{content}"
    elif input_type == "Texto" and text_input:
        document = text_input
    
    if document:
        messages = [
            {
                "role": "system",
                "content": f"Eres un asistente de IA que genera sugerencias de temas para {content_type}(s) basado en el contenido proporcionado y tomando inspiración de las siguientes publicaciones de LinkedIn: {inspiration_posts}. Genera una lista numerada de {st.session_state.suggestions_num} sugerencias de temas. Retorna en el siguiente formato:\n1. [primera sugestion]\n2. [segunda sugestion]\n3. [tercera sugestion]\n..."
            },
            {
                "role": "user",
                "content": f"Genera {st.session_state.suggestions_num} sugerencias de temas para {content_type} basadas en el siguiente contenido: {document[:100_000]}"
            }
        ]

        # Generate content suggestions using the OpenAI API
        st.write(f"Generando sugerencias de temas para {content_type}...")
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )
        
        st.session_state.content_suggestions = response.choices[0].message.content.split('\n')
        st.session_state.generated_contents = {}
    else:
        st.error("Por favor, proporciona contenido para generar sugerencias.")

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
                            "content": f"Eres un asistente de IA que genera {content_type}(s) basado en un tema seleccionado.  Si el contenido es un post de linkedin, manten una estructura clara y usa pocos emojis. Solo retorna el contenido:"
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
                    )

                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            generated_content += chunk.choices[0].delta.content
                            st.session_state.generated_contents[f"generated_content_{i}"] = generated_content
                    
                    # st.rerun()

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
                    st.text(f"Refinando contenido...")
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