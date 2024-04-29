import streamlit as st
import requests
import textwrap
import sqlite3
from collections import Counter

# Set page config
st.set_page_config(page_title="Open Library Search", layout="wide")

# Establish a database connection and create a table if not exists
def create_db_connection():
    conn = sqlite3.connect('books.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS saved_books
    (id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT)
    ''')
    conn.commit()
    return conn, c

# Function to save a selected book to the database
def save_book(book, cursor, connection):
    try:
        book_data = (
            book['id'],
            book['title'],
            book['authors'],
            book['published_date'],
            ", ".join(book['categories']),
            book['description'],
            book['link']
        )
        cursor.execute("INSERT INTO saved_books VALUES (?, ?, ?, ?, ?, ?, ?)", book_data)
        connection.commit()
    except sqlite3.IntegrityError as e:
        st.error(f"Error saving the book: {e}")

# Function to get book details from Open Library API
@st.cache(allow_output_mutation=True, show_spinner=False)
def get_book_details(book_key):
    url = f"https://openlibrary.org{book_key}.json"
    response = requests.get(url)
    if response.status_code == 200:
        book_data = response.json()
        description = book_data.get('description', 'No description available.')
        if isinstance(description, dict):
            description = description.get('value', 'No description available.')
        return textwrap.fill(description, width=80)
    return 'No description available.'

# Function to search books using Open Library API
@st.cache(show_spinner=False, ttl=3600)  # Cache results for 1 hour
def search_books(query, author=None, genre=None, year=None, page=1):
    query_parts = [query]
    if author:
        query_parts.append(f"author:{author}")
    if genre:
        query_parts.append(f"subject:{genre}")
    if year:
        query_parts.append(f"date:{year}")

    query_string = '+'.join(query_parts)
    url = f"https://openlibrary.org/search.json?q={query_string}&page={page}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Initialize session state for pagination and search results
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []

conn, c = create_db_connection()  # Initialize database connection

# Streamlit interface for book search
st.title("Open Library Search and Save Tool")
query = st.text_input("Enter a book title or keyword:")
author = st.text_input("Author (optional):")
genre = st.text_input("Genre (optional):")
year = st.text_input("Publication Year (optional):")

if st.button("Search"):
    st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])
    st.session_state['page'] = 1  # Reset to first page when a new search is performed

# Display search results and handle pagination
if st.session_state['search_results']:
    books = st.session_state['search_results']['docs']
    page = st.session_state['page']
    start_index = (page - 1) * 10
    end_index = start_index + 10
    displayed_books = books[start_index:end_index]

    for book in displayed_books:
        genres = book.get('subject', [])
        top_genres = ", ".join(genres[:5]) if genres else "No Genres Available"
        st.subheader(f"{book['title']} ({book.get('first_publish_year', 'No Date Available')})")
        st.markdown(f"**Author(s):** {', '.join(book.get('author_name', ['Unknown Author']))}")
        st.markdown(f"**Genre:** {top_genres}")
        description = get_book_details(book['key'])
        st.markdown(f"**Description:** {description}")
        st.markdown(f"[More Info](https://openlibrary.org{book['key']})")
        if st.button("Save", key=f"save_{book['key']}"):
            save_book({
                'id': book['key'].split('/')[-1],
                'title': book['title'],
                'authors': ', '.join(book.get('author_name', [])),
                'published_date': book.get('first_publish_year', 'No Date Available'),
                'categories': genres,
                'description': description,
                'link': f"https://openlibrary.org{book['key']}"
            }, c, conn)

    # Pagination buttons
    col1, col2 = st.columns(2)
    with col1:
        if page > 1 and st.button("Previous Page"):
            st.session_state.page -= 1
    with col2:
        if end_index < len(books) and st.button("Next Page"):
            st.session_state.page += 1

conn.close()  # Close the database connection when done
