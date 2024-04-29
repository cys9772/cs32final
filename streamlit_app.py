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

# Function to search books using Open Library API
def search_books(query, author=None, genre=None, year=None):
    query_parts = [query]
    if author:
        query_parts.append(f"author:{author}")
    if genre:
        query_parts.append(f"subject:{genre}")
    if year:
        query_parts.append(f"date:{year}")

    query_string = '+'.join(query_parts)
    url = f"https://openlibrary.org/search.json?q={query_string}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Function to fetch detailed book data
def get_book_details(book_key):
    url = f"https://openlibrary.org{book_key}.json"
    response = requests.get(url)
    if response.status_code == 200:
        book_data = response.json()
        description = book_data.get('description', 'No description available.')
        if isinstance(description, dict):
            description = description.get('value', 'No description available.')
        return description
    return 'No description available.'

# Function to format the search results for display
def format_search_results(search_results):
    if not search_results or 'docs' not in search_results:
        return [], []

    genre_count = Counter()
    books_list = []
    for item in search_results['docs']:
        book_info = {
            'key': item.get('key', ''),
            'title': item.get('title', 'No Title Available'),
            'authors': ", ".join(item.get('author_name', ['Unknown Author'])),
            'published_date': item.get('publish_year', ['No Date Available'])[0],
            'categories': item.get('subject', ['No Genre Available']),
            'description': 'Click "Get Description" to load',
            'link': f"https://openlibrary.org{item.get('key', '')}"
        }
        books_list.append(book_info)
        genre_count.update(book_info['categories'])

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
    search_results = search_books(query, author, genre, year)
    books, most_common_genres = format_search_results(search_results)
    st.write(f"Top 5 Genres: {', '.join(most_common_genres)}")
    if books:
        for book in books:
            st.subheader(f"{book['title']} ({book['published_date']})")
            st.markdown(f"**Author(s):** {book['authors']}")
            st.markdown(f"**Genre:** {', '.join([genre for genre in book['categories'] if genre in most_common_genres])}")
            if st.button("Get Description", key=book['key']):
                description = get_book_details(book['key'])
                book['description'] = description
                st.markdown(f"**Description:** {textwrap.shorten(description, width=250, placeholder='...')}")
            else:
                st.markdown("**Description:** Click 'Get Description' to load")
            st.markdown(f"[More Info]({book['link']})")
            if st.button("Save", key='save_' + book['key']):
                save_book(book)

# Function to save a selected book to the database
def save_book(book):
    book_data = (
        book['key'].split('/')[-1],
        book['title'],
        book['authors'],
        book['published_date'],
        ", ".join(book['categories']),
        book['description'],
        book['link']
    )
    c.execute("INSERT INTO saved_books VALUES (?, ?, ?, ?, ?, ?, ?)", book_data)
    conn.commit()
    st.success("Book saved successfully!")

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
