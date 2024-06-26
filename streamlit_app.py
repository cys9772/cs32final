import streamlit as st
import requests
import textwrap
import sqlite3

# Set the configuration for the page, including the title
st.set_page_config(page_title="Shen-Hwang CS32 Final Project", layout="wide")

# Centering the title
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.title("Shen-Hwang CS32 Final Project")

# Loading SQLite database connection and creating a table for future use
conn = sqlite3.connect('books.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS saved_books
(id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT, image_url TEXT)
''')
conn.commit()

# Save book function -- checks for duplicates first
def save_book(book):
    try:
        c.execute("SELECT id FROM saved_books WHERE id = ?", (book['id'],))
        exists = c.fetchone()
        if not exists:
            c.execute("INSERT INTO saved_books VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                book['id'],
                book['title'],
                book['authors'],
                book['published_date'],
                ", ".join(book['categories']),
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

# Get book details from Open Library API (image, description, author, etc)
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

# Search book function based on user input
def search_books(query, page=1):
    url = f"https://openlibrary.org/search.json?q={query}&page={page}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Main interface setup
st.title("Open Library Search and Save Tool")
query = st.text_input("Enter a book title or keyword:")

if st.button("Search"):
    st.session_state.search_results = search_books(query, 1)
    st.session_state.page = 1

# Search result display and show filtering options
if 'search_results' in st.session_state and st.session_state.search_results:
    books = st.session_state.search_results['docs']
    genre_options = sorted(set(g for book in books for g in book.get('subject', [])))
    author_options = sorted(set(a.lower() for book in books for a in book.get('author_name', [])))
    years = sorted(set(y for book in books for y in book.get('publish_year', [])))

    # Filtering by genre, author, and year (slider)
    selected_genres = st.multiselect("Filter by Genre", options=genre_options)
    selected_authors = st.multiselect("Filter by Author", options=author_options)
    year_range = st.slider("Filter by Year Range", int(min(years)), int(max(years)), (int(min(years)), int(max(years))))

    if selected_genres:
        books = [book for book in books if set(book.get('subject', [])).intersection(selected_genres)]
    if selected_authors:
        books = [book for book in books if set(a.lower() for a in book.get('author_name', [])).intersection(set(selected_authors))]
    books = [book for book in books if year_range[0] <= int(book.get('first_publish_year', year_range[0])) <= year_range[1]]

    # Stay in the current session
    page = st.session_state.page
    start_index = (page - 1) * 10
    end_index = start_index + 10
    displayed_books = books[start_index:end_index]

    # Book display and UI formating with markdown to make things look nicer
    for book in displayed_books:
        col1, col2 = st.columns([1, 5])
        description, cover_url = get_book_details(book['key'])
        with col1:
            st.image(cover_url, width=100, use_column_width=True)
        with col2:
            st.subheader(f"{book['title']} ({book.get('first_publish_year', 'No Date Available')})")
            st.markdown(f"**Author(s):** {', '.join(book.get('author_name', ['Unknown Author']))}")
            st.markdown(f"**Genre:** {', '.join(book.get('subject', [])[:5])}")
            st.markdown(f"**Description:** {description}")
            st.markdown(f"[More Info](https://openlibrary.org{book['key']})")
            if st.button("Save", key=f"save_{book['key']}"):
                save_book({
                    'id': book['key'].split('/')[-1],
                    'title': book['title'],
                    'authors': ', '.join(book.get('author_name', [])),
                    'published_date': book.get('first_publish_year', 'No Date Available'),
                    'categories': book.get('subject', []),
                    'description': description,
                    'link': f"https://openlibrary.org{book['key']}",
                    'image_url': cover_url
                })

    # Page scrolling setup (next and previous)
    col1, col2 = st.columns(2)
    with col1:
        if page > 1 and st.button("Previous Page"):
            st.session_state.page -= 1
    with col2:
        if end_index < len(books) and st.button("Next Page"):
            st.session_state.page += 1

# Saving and deleting book list that users save
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

# Deleting saved books in the session
if st.button("Clear All Saved Books"):
    c.execute("DELETE FROM saved_books")
    conn.commit()
    st.success("All saved books cleared.")

# Close the database connection
conn.close()
