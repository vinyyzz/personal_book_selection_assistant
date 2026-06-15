# app.py - Main Flask Application
import os
import uuid
import re
import requests
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from model import get_model, predict_recommendation
from data_manager import DataManager

app = Flask(__name__)
data_manager = DataManager()
app.secret_key = "book-recommender-secret-2024"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

try:
    pytesseract.get_tesseract_version()
except:
    for path in ['/usr/local/bin/tesseract', '/opt/homebrew/bin/tesseract']:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break


# =============================================
# BOOK DATA FETCHING
# =============================================
def get_book_data(book_name):
    """Fetch book data from OpenLibrary API with better descriptions."""
    search_url = "https://openlibrary.org/search.json"
    
    params = {'title': book_name, 'limit': 1}
    
    print(f"Calling API: {search_url} with params {params}")
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        print(f"API Status: {response.status_code}")
        
        if response.status_code != 200:
            return None, None, None, None, None, None
        
        data = response.json()
        print(f"Results found: {data.get('numFound', 0)}")
        
        if 'docs' not in data or len(data['docs']) == 0:
            return None, None, None, None, None, None
        
        book = data['docs'][0]
        
        title = book.get('title', 'Unknown Title')
        authors = book.get('author_name', ['Unknown Author'])
        
        # Description fetching
        description = ""
        
        if book.get('first_sentence'):
            if isinstance(book['first_sentence'], list):
                description = book['first_sentence'][0]
            else:
                description = str(book['first_sentence'])
        
        work_key = book.get('key', '')
        if (not description or len(description) < 50) and work_key:
            try:
                work_url = f"https://openlibrary.org{work_key}.json"
                work_response = requests.get(work_url, timeout=5)
                if work_response.status_code == 200:
                    work_data = work_response.json()
                    work_desc = work_data.get('description', '')
                    if isinstance(work_desc, dict):
                        work_desc = work_desc.get('value', '')
                    if work_desc and len(str(work_desc)) > len(description):
                        description = str(work_desc)
            except:
                pass
        
        subjects = book.get('subject', [])
        if not description and subjects:
            description = f"This book covers: {', '.join(subjects[:8])}."
        
        if not description and book.get('subtitle'):
            description = f"{title}: {book.get('subtitle')}"
        
        if not description:
            description = f"A book by {', '.join(authors) if isinstance(authors, list) else authors}."
        
        print(f"Description: {description[:100]}...")
        
        # Cover image
        thumbnail = ''
        cover_id = book.get('cover_i')
        if cover_id:
            thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
        elif book.get('isbn'):
            isbn = book['isbn'][0] if isinstance(book['isbn'], list) else book['isbn']
            thumbnail = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
        
        categories = book.get('subject', [])[:5]
        published_date = str(book.get('first_publish_year', ''))
        
        # Save to SQLite
        save_book_for_training(title, description, categories)
        
        return title, authors, description, thumbnail, categories, published_date
        
    except Exception as e:
        print(f"Error fetching book: {e}")
        return None, None, None, None, None, None


def save_book_for_training(title, description, categories):
    """Save book metadata to SQLite."""
    try:
        book_data = {
            'title': title,
            'authors': '',
            'description': description,
            'categories': categories,
            'published_date': '',
            'thumbnail': ''
        }
        data_manager.save_book(book_data)
    except Exception as e:
        print(f"Error saving book: {e}")


# =============================================
# RECOMMENDATION
# =============================================
def get_recommendation(description, title="", categories=None):
    full_text = f"{title} {description} "
    if categories:
        full_text += ' '.join(categories)
    return predict_recommendation(full_text)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# =============================================
# ROUTES
# =============================================
@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
    
    rating_count = data_manager.get_rating_count()
    model = get_model()
    model_status = "Trained (TF-IDF)" if model.is_trained else "Untrained"
    
    return render_template('index.html', rating_count=rating_count, model_status=model_status)


@app.route('/recommend/text', methods=['POST'])
def recommend_text():
    book_title = request.form.get('book_title', '').strip()
    
    if not book_title:
        flash('Please enter a book title.', 'error')
        return redirect(url_for('index'))
    
    result = get_book_data(book_title)
    
    if result[0] is None:
        flash(f'Book "{book_title}" not found.', 'error')
        return redirect(url_for('index'))
    
    title, authors, description, thumbnail, categories, published_date = result
    category, confidence, probabilities = get_recommendation(description, title, categories)
    
    session['last_book'] = title
    
    book_data = {
        'title': title,
        'authors': authors if isinstance(authors, list) else [authors],
        'description': description,
        'thumbnail': thumbnail,
        'categories': categories,
        'published_date': published_date
    }
    
    return render_template('result.html',
                         book=book_data,
                         recommendation=category,
                         confidence=f"{confidence:.1%}",
                         probabilities=probabilities)


@app.route('/recommend/image', methods=['POST'])
def recommend_image():
    if 'book_image' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('index'))
    
    file = request.files['book_image']
    
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)
        
        try:
            img = Image.open(filepath)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            img = img.convert('L')
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            img = img.filter(ImageFilter.SHARPEN)
            
            clean_path = filepath.rsplit('.', 1)[0] + '_clean.png'
            img.save(clean_path, 'PNG')
            
            text = pytesseract.image_to_string(Image.open(clean_path))
            
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            candidates = []
            for line in lines:
                cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', line).strip()
                if len(cleaned) > 3 and len(cleaned) < 100:
                    candidates.append(cleaned)
            
            detected = candidates[0] if candidates else ''
            
            if not detected:
                text2 = pytesseract.image_to_string(Image.open(filepath))
                for line in text2.split('\n'):
                    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', line.strip()).strip()
                    if len(cleaned) > 3:
                        candidates.append(cleaned)
                detected = candidates[0] if candidates else ''
            
            session['ocr_detected'] = detected
            session['ocr_candidates'] = candidates[:5]
            
            if os.path.exists(clean_path):
                os.remove(clean_path)
            
            return render_template('confirm_ocr.html', detected=detected, candidates=candidates[:5])
            
        except Exception as e:
            flash('Error processing image.', 'error')
            return redirect(url_for('index'))
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        flash('Invalid file type.', 'error')
    
    return redirect(url_for('index'))


@app.route('/recommend/confirm', methods=['POST'])
def recommend_confirm():
    book_title = request.form.get('book_title', '').strip()
    
    if not book_title:
        flash('Please enter a book title.', 'error')
        return redirect(url_for('index'))
    
    result = get_book_data(book_title)
    
    if result[0] is None:
        flash(f'Book "{book_title}" not found.', 'error')
        return redirect(url_for('index'))
    
    title, authors, description, thumbnail, categories, published_date = result
    category, confidence, probabilities = get_recommendation(description, title, categories)
    
    book_data = {
        'title': title,
        'authors': authors if isinstance(authors, list) else [authors],
        'description': description,
        'thumbnail': thumbnail,
        'categories': categories,
        'published_date': published_date
    }
    
    return render_template('result.html',
                         book=book_data,
                         recommendation=category,
                         confidence=f"{confidence:.1%}",
                         probabilities=probabilities,
                         ocr_text=book_title)


@app.route('/feedback/rate', methods=['POST'])
def add_rating():
    book_title = request.form.get('book_title')
    rating = request.form.get('rating')
    
    if book_title and rating:
        try:
            rating_val = int(rating)
            if 1 <= rating_val <= 5:
                user_id = session.get('user_id', 'anonymous')
                data_manager.save_rating(user_id, book_title, rating_val)
                flash(f'Thanks! You rated "{book_title}" {rating_val} stars.', 'success')
                
                # Auto-retrain
                count = data_manager.get_rating_count()
                if count >= 5 and count % 3 == 0:
                    model = get_model()
                    metrics = model.retrain_from_ratings()
                    if metrics.get('accuracy', 0) > 0:
                        flash(f'Model retrained! Accuracy: {metrics["accuracy"]:.1%}', 'info')
            else:
                flash('Rating must be between 1 and 5.', 'error')
        except Exception as e:
            print(f"Rating error: {e}")
            flash('Invalid rating.', 'error')
    else:
        flash('Missing book or rating.', 'error')
    
    return redirect(url_for('index'))


@app.route('/history')
def view_history():
    user_id = session.get('user_id', 'anonymous')
    ratings = data_manager.get_user_ratings(user_id)
    return render_template('history.html', ratings=ratings)


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error="Page not found"), 404


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5002)