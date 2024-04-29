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
conn.commit()

# Initialize session state for pagination and search results
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None
if 'search_triggered' not in st.session_state:
    st.session_state['search_triggered'] = False

# Function to search books using Open Library API
@st.experimental_memo
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

# Function to format the search results for display
def format_search_results(search_results):
    if not search_results or 'docs' not in search_results:
        return [], []

    genre_count = Counter()
    books_list = []
    for item in search_results['docs']:
        book_key = item.get('key', '')
        publish_year = item.get('publish_year', [])
        published_date = str(min(publish_year)) if publish_year else "No Date Available"

        book_info = {
            'key': book_key,
            'id': book_key.split('/')[-1],
            'title': item.get('title', 'No Title Available'),
            'authors': ", ".join(item.get('author_name', ['Unknown Author'])),
            'published_date': published_date,
            'categories': item.get('subject', ['No Genre Available']),
            'description': 'Click "Get Description" to load',
            'link': f"https://openlibrary.org{book_key}"
        }
        books_list.append(book_info)
        genre_count.update(item.get('subject', []))

    most_common_genres = [genre for genre, count in genre_count.most_common(5)]
    return books_list, most_common_genres

# Streamlit interface for book search
st.title("Open Library Search and Save Tool")

# Search inputs
query = st.text_input("Enter a book title or keyword:")
author = st.text_input("Author (optional):")
genre = st.text_input("Genre (optional):")
year = st.text_input("Publication Year (optional):")

# Search action
if st.button("Search"):
    st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])
    st.session_state['search_triggered'] = True
    st.session_state['page'] = 1  # Reset to first page

# Display search results and pagination buttons only if search has been triggered
if st.session_state['search_triggered'] and st.session_state['search_results']:
    books, most_common_genres = format_search_results(st.session_state['search_results'])
    st.write(f"Top 5 Genres: {', '.join(most_common_genres)}")

    for book in books:
        st.subheader(f"{book['title']} ({book['published_date']})")
        st.markdown(f"**Author(s):** {book['authors']}")
        st.markdown(f"**Genre:** {', '.join([genre for genre in book['categories'] if genre in most_common_genres])}")
        if st.button("Get Description", key='desc_'+book['id']):
            book['description'], _ = get_book_details(book['key'])
        st.markdown(f"**Description:** {book['description']}")
        st.markdown(f"[More Info]({book['link']})")
        if st.button("Save", key='save_'+book['id']):
            save_book(book)
            st.success("Book saved successfully!")

    # Pagination buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous"):
            if st.session_state['page'] > 1:
                st.session_state['page'] -= 1
                st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])
    with col2:
        if st.button("Next"):
            st.session_state['page'] += 1
            st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])

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
