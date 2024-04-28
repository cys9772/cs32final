import streamlit as st
import requests
import textwrap
import sqlite3

# Database setup
conn = sqlite3.connect('books.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS saved_books
(id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT)
''')
conn.commit()

# Function to search books using Open Library
def search_books(query):
    url = f"https://openlibrary.org/search.json?q={query}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch books. Error {response.status_code}: {response.text}")
        return None

# Function to fetch detailed book data
def get_book_details(book_key):
    url = f"https://openlibrary.org{book_key}.json"
    response = requests.get(url)
    if response.status_code == 200:
        book_data = response.json()
        description = book_data.get('description')
        if isinstance(description, dict):
            description = description.get('value', 'No description available.')
        return description
    else:
        return 'No description available.'

# Function to format search results from Open Library
def format_search_results(search_results):
    books = search_results.get('docs', [])
    formatted_books = []
    for book in books:
        book_key = book.get('key')
        genres = book.get('subject', [])
        top_genres = ", ".join(genres[:5]) if genres else "No Genres Available"

        description = get_book_details(book_key) or 'No description available.'

        book_info = {
            'id': book_key.split('/')[-1],
            'title': book.get('title', 'No Title Available'),
            'authors': ", ".join(book.get('author_name', ['Unknown Author'])),
            'published_date': book.get('publish_date', ['No Date Available'])[0],
            'categories': top_genres,
            'description': description,
            'link': f"https://openlibrary.org{book_key}"
        }
        formatted_books.append(book_info)
    return formatted_books

# Streamlit interface
st.title("Book Search and Save Tool")

# Search books
search_query = st.text_input("Enter book title or author:")
if st.button("Search"):
    search_results = search_books(search_query)
    if search_results:
        books = format_search_results(search_results)
        for book in books:
            st.subheader(f"{book['title']} ({book['published_date']})")
            st.markdown(f"**Author(s):** {book['authors']}")
            st.markdown(f"**Genre:** {book['categories']}")
            st.markdown(f"**Description:** {textwrap.shorten(book['description'], width=250, placeholder='...')}")
            st.markdown(f"[More Info]({book['link']})")
            if st.button("Save", key=book['id']):
                save_book(book)
                st.success("Book saved successfully!")

# Function to save books to the database
def save_book(book):
    book_data = (
        book['id'],
        book['title'],
        book['authors'],
        book['published_date'],
        book['categories'],
        book['description'],
        book['link']
    )
    c.execute("INSERT INTO saved_books VALUES (?, ?, ?, ?, ?, ?, ?)", book_data)
    conn.commit()

# Function to show saved books
if st.button("Show Saved Books"):
    c.execute("SELECT * FROM saved_books")
    saved_books = c.fetchall()
    if saved_books:
        for book in saved_books:
            st.text(f"ID: {book[0]}\nTitle: {book[1]}\nAuthor(s): {book[2]}\nYear: {book[3]}\nGenre: {book[4]}\nDescription: {textwrap.fill(book[5], width=80)}\nLink: {book[6]}\n")
    else:
        st.write("No saved books.")

# Clear all saved books
if st.button("Clear Saved Books"):
    c.execute("DELETE FROM saved_books")
    conn.commit()
    st.success("All saved books cleared.")
