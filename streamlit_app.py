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

# Constants
RESULTS_PER_PAGE = 10  # Number of results per page

# Google Books API key
api_key = 'YOUR_API_KEY_HERE'  # Replace 'YOUR_API_KEY_HERE' with your actual Google Books API key

# Function to search books using Google Books API
def search_books(query, author=None, genre=None, year=None):
    query_parts = [query]
    if author:
        query_parts.append(f"inauthor:{author}")
    if genre:
        query_parts.append(f"subject:{genre}")
    if year:
        query_parts.append(f"inpublisher:{year}")

    query_string = '+'.join(query_parts)
    url = f"https://www.googleapis.com/books/v1/volumes?q={query_string}&key={api_key}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Function to format the search results for display
def format_search_results(search_results):
    if 'items' not in search_results:
        return [], [], []
    books_list = []
    genres = set()
    years = set()
    for item in search_results['items']:
        volume_info = item['volumeInfo']
        genres.update(volume_info.get('categories', []))
        years.add(volume_info.get('publishedDate', '')[0:4])
        book_info = {
            'id': item['id'],
            'title': volume_info.get('title', 'No Title Available'),
            'authors': ", ".join(volume_info.get('authors', ['Unknown Author'])),
            'published_date': volume_info.get('publishedDate', 'No Date Available')[:4],
            'categories': ", ".join(volume_info.get('categories', ['No Genre Available'])),
            'description': textwrap.fill(volume_info.get('description', 'No Description Available'), width=80),
            'link': volume_info.get('infoLink', '#')
        }
        books_list.append(book_info)
    genres = sorted(list(genres))
    years = sorted(list(years))
    return books_list, genres, years

# Streamlit interface for book search
st.title("Google Books Search and Save Tool")

# Search inputs
query = st.text_input("Enter a book title or keyword:")
author = st.text_input("Author (optional):")
genre = st.text_input("Genre (optional):")
year = st.text_input("Publication Year (optional):")

if st.button("Search"):
    search_results = search_books(query, author, genre, year)
    books, available_genres, available_years = format_search_results(search_results)
    if books:
        for book in books:
            st.subheader(f"{book['title']} ({book['published_date']})")
            st.markdown(f"**Author(s):** {book['authors']}")
            st.markdown(f"**Genre:** {book['categories']}")
            st.markdown(f"**Description:** {book['description']}")
            st.markdown(f"[More Info]({book['link']})")
            if st.button("Save", key=book['id']):
                save_book(book['id'])
                st.success("Book saved successfully!")

# Function to save a selected book to the database
def save_book(book_id):
    url = f"https://www.googleapis.com/books/v1/volumes/{book_id}?key={api_key}"
    response = requests.get(url).json()
    volume_info = response['volumeInfo']
    book_data = (
        book_id,
        volume_info.get('title', 'No Title Available'),
        ", ".join(volume_info.get('authors', ['Unknown Author'])),
        volume_info.get('publishedDate', 'No Date Available')[:4],
        ", ".join(volume_info.get('categories', ['No Genre Available'])),
        volume_info.get('description', 'No Description Available'),
        volume_info.get('infoLink', '#')
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
