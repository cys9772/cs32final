import streamlit as st
import requests
import textwrap
import sqlite3
from collections import Counter

# Set page config
st.set_page_config(page_title="Open Library Search", layout="wide")

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
        description = get_book_details(book_key)  # Fetch description immediately
        published_date = item.get('first_publish_year', 'No Date Available')

        book_info = {
            'key': book_key,
            'id': book_key.split('/')[-1],
            'title': item.get('title', 'No Title Available'),
            'authors': ", ".join(item.get('author_name', ['Unknown Author'])),
            'published_date': published_date,
            'categories': item.get('subject', ['No Genre Available']),
            'description': description,
            'link': f"https://openlibrary.org{book_key}"
        }
        books_list.append(book_info)
        genre_count.update(item.get('subject', []))

    most_common_genres = [genre for genre, count in genre_count.most_common(5)]
    return books_list, most_common_genres

# Initialize session state for pagination and search results
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

# Streamlit interface for book search
st.title("Open Library Search and Save Tool")

# Search inputs
query = st.text_input("Enter a book title or keyword:")
author = st.text_input("Author (optional):")
genre = st.text_input("Genre (optional):")
year = st.text_input("Publication Year (optional):")

# Handle search and pagination
if st.button("Search"):
    st.session_state.search_results = search_books(query, author, genre, year, st.session_state.page)
    st.session_state.page = 1  # Reset to first page when new search is made

# Display search results and pagination buttons only if search has been triggered
if st.session_state.search_results:
    books, most_common_genres = format_search_results(st.session_state.search_results)
    st.write(f"Top 5 Genres: {', '.join(most_common_genres)}")
    for book in books[:10]:  # Display the top 10 results
        st.subheader(f"{book['title']} ({book['published_date']})")
        st.markdown(f"**Author(s):** {book['authors']}")
        st.markdown(f"**Genre:** {', '.join([genre for genre in book['categories'] if genre in most_common_genres])}")
        st.markdown(f"**Description:** {book['description']}")
        st.markdown(f"[More Info]({book['link']})")
        if st.button("Save", key='save_'+book['id']):
            save_book(book)
            st.success(f"Book saved successfully: {book['title']}")

# Pagination buttons
if len(st.session_state.search_results.get('docs', [])) > 10:
    st.write("---")  # Separator
    prev, _, next = st.columns([1, 10, 1])
    with prev:
        if st.button("Previous Page"):
            if st.session_state.page > 1:
                st.session_state.page -= 1
                st.session_state.search_results = search_books(query, author, genre, year, st.session_state.page)
    with next:
        if st.button("Next Page"):
            st.session_state.page += 1
            st.session_state.search_results = search_books(query, author, genre, year, st.session_state.page)

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
