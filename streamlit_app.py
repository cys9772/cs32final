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
conn.commit()

# Initialize session state for pagination and search results
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None
if 'search_triggered' not in st.session_state:
    st.session_state['search_triggered'] = False

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
def format_search_results(search_results, page):
    if not search_results or 'docs' not in search_results:
        return [], []

    # Pagination: calculate start and end indices for the current page
    start_index = (page - 1) * 10
    end_index = start_index + 10

    genre_count = Counter()
    books_list = []
    for item in search_results['docs'][start_index:end_index]:
        # Attempt to get the publish_date if present
        publish_date = item.get('first_publish_year', 'No publish date available.')

        book_info = {
            'id': item.get('key', '').split('/')[-1],
            'title': item.get('title', 'No Title Available'),
            'authors': ", ".join(item.get('author_name', ['Unknown Author'])),
            'published_date': publish_date,
            'categories': item.get('subject', ['No Genre Available']),
            'description': item.get('description', 'No Description Available'),
            'link': f"https://openlibrary.org{item.get('key', '')}"
        }
        books_list.append(book_info)
        genre_count.update(item.get('subject', []))

    # Select the top 5 most common genres
    most_common_genres = [genre for genre, count in genre_count.most_common(5)]
    return books_list, most_common_genres

# Streamlit interface for book search
st.title("Open Library Search and Save Tool")

# Search inputs
query = st.text_input("Enter a book title or keyword:")
author = st.text_input("Author (optional):")
genre = st.text_input("Genre (optional):")
year = st.text_input("Publication Year (optional):")

if st.button("Search"):
    st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])
    st.session_state['search_triggered'] = True
    st.session_state['page'] = 1  # Reset to first page

# Display search results and pagination buttons only if search has been triggered
if st.session_state['search_triggered']:
    # Pagination
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Previous"):
            if st.session_state['page'] > 1:
                st.session_state['page'] -= 1
                st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])
    with col3:
        if st.button("Next"):
            st.session_state['page'] += 1
            st.session_state['search_results'] = search_books(query, author, genre, year, st.session_state['page'])

    # Display search results
    if st.session_state['search_results']:
        books, most_common_genres = format_search_results(st.session_state['search_results'], st.session_state['page'])
        st.write(f"Top 5 Genres: {', '.join(most_common_genres)}")
        if books:
            for book in books:
                st.subheader(f"{book['title']} ({book['published_date']})")
                st.markdown(f"**Author(s):** {book['authors']}")
                st.markdown(f"**Genre:** {', '.join([genre for genre in book['categories'] if genre in most_common_genres])}")
                st.markdown(f"**Description:** {book['description']}")
                st.markdown(f"[More Info]({book['link']})")
                if st.button("Save", key=book['id']):
                    save_book(book)
                    st.success("Book saved successfully!")
