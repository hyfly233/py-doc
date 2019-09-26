import numpy as np


def process_docx(file_path):
    from docx import Document

    # Load the DOCX file
    doc = Document(file_path)
    text = []

    # Extract text from each paragraph in the document
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)

    # Join the text into a single string
    full_text = "\n".join(text)

    # Here you can implement any additional processing, such as tokenization or embedding
    # For simplicity, we will just return the full text
    return full_text


def prepare_for_indexing(text):
    # This function can be used to convert the text into a format suitable for FAISS indexing
    # For example, you might want to convert the text into embeddings using a model
    # Here we will just return a dummy numpy array for demonstration purposes
    # In practice, you would use a model to generate embeddings
    return np.random.rand(128).astype('float32')  # Example: 128-dimensional vector


def process_and_index_docx(file_path, faiss_index):
    text = process_docx(file_path)
    vector = prepare_for_indexing(text)

    # Add the vector to the FAISS index
    faiss_index.add(np.array([vector]))  # FAISS expects a 2D array
    return text  # Return the extracted text for reference
