import requests
import textwrap
import sqlite3

conn = sqlite3.connect('books.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS saved_books
             (id TEXT PRIMARY KEY, title TEXT, author TEXT, published_date TEXT, categories TEXT, description TEXT, link TEXT)''')
conn.commit()

def search_books(query):
    api_key = 'AIzaSyAbfSW_rnPaf6vG8aNbsQ_Lsq7Ny8L6zko'
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error occurred while searching for books.")
        return None

def format_search_results(search_results):
    books_list = []
    if 'items' in search_results:
        for item in search_results['items']:
            id = item['id']
            volume_info = item['volumeInfo']
            title = volume_info.get('title', 'No Title Available')
            authors = ", ".join(volume_info.get('authors', ['Unknown Author']))
            published_date = volume_info.get('publishedDate', 'No Date Available')[:4]
            categories = ", ".join(volume_info.get('categories', ['No Genre Available']))
            description = volume_info.get('description', 'No Description Available')

            wrapped_description = textwrap.fill(description, width=80)

            link = volume_info.get('infoLink', '#')

            book_info = f"ID: {id}\nTitle: {title}\nAuthor(s): {authors}\nYear: {published_date}\nGenre: {categories}\nDescription:\n{wrapped_description}\nLink: {link}\n"
            books_list.append(book_info)
    else:
        books_list.append("No results found.")
    return "\n".join(books_list)

def save_book(book_id):
    api_key = 'AIzaSyAbfSW_rnPaf6vG8aNbsQ_Lsq7Ny8L6zko'
    url = f"https://www.googleapis.com/books/v1/volumes/{book_id}?key={api_key}"
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

def show_saved_books():
    c.execute("SELECT * FROM saved_books")
    saved_books = c.fetchall()
    if saved_books:
        books_list = []
        for book in saved_books:
            id, title, author, published_date, categories, description, link = book
            book_info = f"ID: {id}\nTitle: {title}\nAuthor(s): {author}\nYear: {published_date}\nGenre: {categories}\nDescription:\n{textwrap.fill(description, width=80)}\nLink: {link}\n"
            books_list.append(book_info)
        return "\n".join(books_list)
    else:
        return "No saved books."

def clear_saved_books():
    c.execute("DELETE FROM saved_books")
    conn.commit()
    print("All saved books cleared.")

search_query = input("Enter book title or author: ")
search_results = search_books(search_query)
formatted_results = format_search_results(search_results)
print(formatted_results)

book_id = input("Enter book ID to save: ")
save_book(book_id)
print("Book saved.")

print(show_saved_books())

clear_saved_books()

conn.close()
