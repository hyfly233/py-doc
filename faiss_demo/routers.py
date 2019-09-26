from flask import Blueprint, request, jsonify
from document_processor import process_docx
# from faiss_index import add_document_to_index, search_index

api = Blueprint('api', __name__)


@api.route('/add_document', methods=['POST'])
def add_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Process the DOCX file and extract text
    text = process_docx(file)
    if text is None:
        return jsonify({'error': 'Failed to process document'}), 500

    # Add the document to the FAISS index
    # add_document_to_index(text)
    return jsonify({'message': 'Document added successfully'}), 201


@api.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Perform a search in the FAISS index
    # results = search_index(query)
    # return jsonify({'results': results}), 200

    pass