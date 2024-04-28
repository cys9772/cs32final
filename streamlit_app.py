import streamlit as st
import requests
import textwrap
import sqlite3

# Database setup
conn = sqlite3.connect('books.db', check_same_thread=False)  # Add check_same_thread=False for Streamlit compatibility
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS saved_books
             (id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT)''')
conn.commit()

# API Key setup
api_key = st.secrets["AIzaSyAbfSW_rnPaf6vG8aNbsQ_Lsq7Ny8L6zko"]

# Function to search books
def search_books(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        if response.status_code == 403:
            st.error("Access denied due to geographic restrictions. This service may not be available in your region.")
        else:
            st.error(f"Failed to fetch books. Error {response.status_code}: {response.text}")
        return None

# Function to format search results
def format_search_results(search_results):
    if 'items' in search_results:
        return search_results['items']
    else:
        return []

# Streamlit interface
st.title("Book Search and Save Tool")

# Search books
search_query = st.text_input("Enter book title or author:")
if st.button("Search"):
    search_results = search_books(search_query)
    if search_results:
        books = format_search_results(search_results)
        for book in books:
            id = book['id']
            volume_info = book['volumeInfo']
            title = volume_info.get('title', 'No Title Available')
            authors = ", ".join(volume_info.get('authors', ['Unknown Author']))
            published_date = volume_info.get('publishedDate', 'No Date Available')[:4]
            categories = ", ".join(volume_info.get('categories', ['No Genre Available']))
            description = volume_info.get('description', 'No Description Available')
            link = volume_info.get('infoLink', '#')

            st.subheader(f"{title} ({published_date})")
            st.write(f"Author(s): {authors}")
            st.write(f"Genre: {categories}")
            st.write(f"Description: {textwrap.shorten(description, width=250, placeholder='...')}")
            st.write(f"[More Info]({link})")
            if st.button("Save", key=id):
                save_book(id)
                st.success("Book saved successfully!")

# Function to save books to the database
def save_book(book_id):
    url = f"https://www.googleapis.com/books/v1/volumes/{book_id}?key={API_KEY}"
    response = requests.get(url).json()
    book_info = response.get('volumeInfo', {})
    book_data = (
        book_id,
        book_info.get('title', 'No Title Available'),
        ", ".join(book_info.get('authors', ['Unknown Author'])),
        book_info.get('publishedDate', 'No Date Available')[:4],
        ", ".join(book_info.get('categories', ['No Genre Available'])),
        book_info.get('description', 'No Description Available'),
        book_info.get('infoLink', '#')
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
