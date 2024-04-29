import streamlit as st
import requests
import textwrap
import sqlite3

# Set page config
st.set_page_config(page_title="Open Library Search", layout="wide")

# Database setup
conn = sqlite3.connect('books.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS saved_books
(id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT, image_url TEXT)
''')
conn.commit()

# Function to save a selected book to the database
def save_book(book):
    try:
        # Check if the book already exists
        c.execute("SELECT id FROM saved_books WHERE id = ?", (book['id'],))
        exists = c.fetchone()
        if not exists:
            # Insert new book entry
            c.execute("INSERT INTO saved_books VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                book['id'],
                book['title'],
                book['authors'],
                book['published_date'],
                ", ".join(book['categories'][:5]),
                book['description'],
                book['link'],
                book['image_url']
            ))
            conn.commit()
            st.success(f"Book saved successfully: {book['title']}")
        else:
            st.warning("Book already exists in the database.")
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
        cover_id = book_data.get('covers', [])[0] if book_data.get('covers', []) else None
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else "https://via.placeholder.com/128x193?text=No+Cover"
        return textwrap.fill(description, width=80), cover_url
    return 'No description available.', "https://via.placeholder.com/128x193?text=No+Cover"

# Function to search books using Open Library API
@st.cache(show_spinner=False, ttl=3600)  # Cache results for 1 hour
def search_books(query, page=1):
    url = f"https://openlibrary.org/search.json?q={query}&page={page}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Streamlit interface for book search
st.title("Open Library Search and Save Tool")
query = st.text_input("Enter a book title or keyword:")

if st.button("Search"):
    st.session_state.search_results = search_books(query, 1)
    st.session_state.page = 1

# Display and manage saved books
if st.button("Show Saved Books"):
    c.execute("SELECT * FROM saved_books")
    saved_books = c.fetchall()
    if saved_books:
        for book in saved_books:
            col1, col2 = st.columns([1, 5])
            with col1:
                st.image(book[7], width=100, use_column_width=True)  # Display saved book cover image
            with col2:
                st.text(f"ID: {book[0]}\nTitle: {book[1]}\nAuthor(s): {book[2]}\nYear: {book[3]}\nGenre: {', '.join(book[4].split(', ')[:5])}\nDescription: {textwrap.fill(book[5], width=80)}\nLink: {book[6]}")
    else:
        st.write("No saved books.")

if st.button("Clear All Saved Books"):
    c.execute("DELETE FROM saved_books")
    conn.commit()
    st.success("All saved books cleared.")

conn.close()
