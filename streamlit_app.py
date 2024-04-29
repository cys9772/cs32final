import streamlit as st
import requests
import textwrap
import sqlite3
from collections import Counter

# Database setup
conn = sqlite3.connect('books.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS saved_books
(id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT)
''')

# Function to save a selected book to the database
def save_book(book):
    book_data = (
        book['id'],
        book['title'],
        book['authors'],
        book['published_date'],
        ", ".join(book['categories']),
        book['description'],
        book['link']
    )
    c.execute("INSERT INTO saved_books VALUES (?, ?, ?, ?, ?, ?, ?)", book_data)
    conn.commit()

# Function to get book details from Open Library API
@st.cache(allow_output_mutation=True)
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
    st.session_state['search_results'] = None
if 'search_triggered' not in st.session_state:
    st.session_state['search_triggered'] = False

# Streamlit interface for book search
st.title("Open Library Search and Save Tool")

# Search inputs
query = st.text_input("Enter a book title or keyword:")
author = st.text_input("Author (optional):")
genre = st.text_input("Genre (optional):")
year = st.text_input("Publication Year (optional):")

# Handle search and pagination
if st.button("Search"):
    st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])
    st.session_state['search_triggered'] = True
    st.session_state['page'] = 1  # Reset to first page when new search is made

# Display search results and pagination buttons only if search has been triggered
if st.session_state['search_triggered'] and st.session_state['search_results']:
    st.write(f"Showing results for page {st.session_state['page']}")
    books = st.session_state['search_results']['docs']
    start_index = (st.session_state['page'] - 1) * 10
    end_index = start_index + 10
    books_to_display = books[start_index:end_index]

    genre_count = Counter([genre for book in books for genre in book.get('subject', [])])
    most_common_genres = [genre for genre, count in genre_count.most_common(5)]
    st.write(f"Top 5 Genres: {', '.join(most_common_genres)}")

    for book in books_to_display:
        st.subheader(f"{book['title']} ({book.get('first_publish_year', 'No Date Available')})")
        st.markdown(f"**Author(s):** {', '.join(book.get('author_name', ['Unknown Author']))}")
        st.markdown(f"**Genre:** {', '.join([genre for genre in book.get('subject', []) if genre in most_common_genres])}")
        description = get_book_details(book['key'])
        st.markdown(f"**Description:** {description}")
        st.markdown(f"[More Info]({f'https://openlibrary.org{book['key']}'}")
        if st.button("Save", key='save_'+book['key']):
            save_book({
                'id': book['key'].split('/')[-1],
                'title': book['title'],
                'authors': ', '.join(book.get('author_name', ['Unknown Author'])),
                'published_date': book.get('first_publish_year', 'No Date Available'),
                'categories': ', '.join(book.get('subject', ['No Genre Available'])),
                'description': description,
                'link': f"https://openlibrary.org{book['key']}"
            })
            st.success(f"Book saved successfully: {book['title']}")

    # Pagination buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous Page") and st.session_state['page'] > 1:
            st.session_state['page'] -= 1
    with col2:
        if st.button("Next Page") and end_index < len(books):
            st.session_state['page'] += 1

# Display saved books
if st.button("Show Saved Books"):
    c.execute("SELECT * FROM saved_books")
    saved_books = c.fetchall()
    if saved_books:
        for book in saved_books:
            st.text(f"ID: {book[0]}\nTitle: {book[1]}\nAuthor(s): {book[2]}\nYear: {book[3]}\nGenre: {book[4]}\nDescription: {textwrap.fill(book[5], width=80)}\nLink: {book[6]}\n")
    else:
        st.write("No saved books.")

# Clear all saved books
if st.button("Clear All Saved Books"):
    c.execute("DELETE FROM saved_books")
    conn.commit()
    st.success("All saved books cleared.")

# Close the database connection
conn.close()
