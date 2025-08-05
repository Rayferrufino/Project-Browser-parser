#!/usr/bin/env python3
"""
Browser History Viewer - A comprehensive tool for analyzing browser history databases
Supports Chrome, Firefox, and Safari SQLite databases
"""

import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import tempfile
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

class BrowserHistoryParser:
    def __init__(self, db_path):
        self.db_path = db_path
        self.browser_type = self.detect_browser_type()
    
    def detect_browser_type(self):
        """Detect browser type based on database structure"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            # Chrome detection
            if 'urls' in tables and 'visits' in tables and 'downloads' in tables:
                return 'chrome'
            # Firefox detection
            elif 'moz_places' in tables and 'moz_historyvisits' in tables:
                return 'firefox'
            # Safari detection
            elif 'history_items' in tables and 'history_visits' in tables:
                return 'safari'
            else:
                return 'unknown'
                
        except Exception as e:
            print(f"Error detecting browser type: {e}")
            return 'unknown'
    
    def chrome_to_timestamp(self, chrome_time):
        """Convert Chrome timestamp to readable format"""
        if chrome_time == 0:
            return "Never"
        # Chrome timestamps are microseconds since Jan 1, 1601 UTC
        epoch_start = datetime(1601, 1, 1, tzinfo=timezone.utc)
        chrome_datetime = epoch_start + timedelta(microseconds=chrome_time)
        return chrome_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    def webkit_to_timestamp(self, webkit_time):
        """Convert WebKit timestamp to readable format"""
        if webkit_time == 0:
            return "Never"
        # WebKit timestamps are seconds since Jan 1, 2001 UTC
        epoch_start = datetime(2001, 1, 1, tzinfo=timezone.utc)
        webkit_datetime = epoch_start + timedelta(seconds=webkit_time)
        return webkit_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    def firefox_to_timestamp(self, firefox_time):
        """Convert Firefox timestamp to readable format"""
        if firefox_time == 0:
            return "Never"
        # Firefox timestamps are microseconds since Unix epoch
        firefox_datetime = datetime.fromtimestamp(firefox_time / 1000000, tz=timezone.utc)
        return firefox_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    def get_history_data(self):
        """Extract history data based on browser type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if self.browser_type == 'chrome':
                query = """
                SELECT 
                    last_visit_time,
                    url,
                    title,
                    visit_count,
                    typed_count,
                    hidden
                FROM urls 
                ORDER BY last_visit_time DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    data.append({
                        'last_visit_time': self.chrome_to_timestamp(row[0]),
                        'url': row[1] or '',
                        'title': row[2] or '',
                        'visit_count': row[3] or 0,
                        'typed_count': row[4] or 0,
                        'is_hidden': 'Yes' if row[5] else 'No'
                    })
                
            elif self.browser_type == 'firefox':
                query = """
                SELECT 
                    last_visit_date,
                    url,
                    title,
                    visit_count,
                    typed,
                    hidden
                FROM moz_places 
                WHERE last_visit_date IS NOT NULL
                ORDER BY last_visit_date DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    data.append({
                        'last_visit_time': self.firefox_to_timestamp(row[0]),
                        'url': row[1] or '',
                        'title': row[2] or '',
                        'visit_count': row[3] or 0,
                        'typed_count': row[4] or 0,
                        'is_hidden': 'Yes' if row[5] else 'No'
                    })
            
            elif self.browser_type == 'safari':
                query = """
                SELECT 
                    visit_time,
                    url,
                    domain_expansion,
                    visit_count
                FROM history_items 
                ORDER BY visit_time DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    data.append({
                        'last_visit_time': self.webkit_to_timestamp(row[0]),
                        'url': row[1] or '',
                        'title': row[2] or '',
                        'visit_count': row[3] or 0,
                        'typed_count': 0,  # Safari doesn't track this
                        'is_hidden': 'No'  # Safari doesn't track this
                    })
            
            conn.close()
            return data
            
        except Exception as e:
            print(f"Error extracting history data: {e}")
            return []
    
    def get_downloads_data(self):
        """Extract downloads data based on browser type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if self.browser_type == 'chrome':
                query = """
                SELECT 
                    start_time,
                    end_time,
                    target_path,
                    received_bytes,
                    total_bytes,
                    tab_url,
                    tab_referrer_url
                FROM downloads 
                ORDER BY start_time DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    path = row[2] or ''
                    filename = os.path.basename(path) if path else ''
                    
                    data.append({
                        'start_time': self.chrome_to_timestamp(row[0]),
                        'end_time': self.chrome_to_timestamp(row[1]),
                        'filename': filename,
                        'path': path,
                        'received_bytes': row[3] or 0,
                        'total_bytes': row[4] or 0,
                        'source_url': row[5] or '',
                        'referrer_url': row[6] or ''
                    })
                
            elif self.browser_type == 'firefox':
                query = """
                SELECT 
                    dateAdded,
                    lastModified,
                    title,
                    content
                FROM moz_anno_attributes aa
                JOIN moz_annos a ON aa.id = a.anno_attribute_id
                JOIN moz_places p ON a.place_id = p.id
                WHERE aa.name = 'downloads/destinationFileURI'
                ORDER BY dateAdded DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    data.append({
                        'start_time': self.firefox_to_timestamp(row[0]),
                        'end_time': self.firefox_to_timestamp(row[1]),
                        'filename': row[2] or '',
                        'path': row[3] or '',
                        'received_bytes': 0,
                        'total_bytes': 0,
                        'source_url': '',
                        'referrer_url': ''
                    })
            
            else:  # Safari and unknown
                data = []
            
            conn.close()
            return data
            
        except Exception as e:
            print(f"Error extracting downloads data: {e}")
            return []
    
    def get_visits_data(self):
        """Extract visits data based on browser type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if self.browser_type == 'chrome':
                query = """
                SELECT 
                    v.visit_time,
                    u.url,
                    u.title,
                    v.transition,
                    ref_u.url as referrer_url,
                    ref_u.title as referrer_title
                FROM visits v
                JOIN urls u ON v.url = u.id
                LEFT JOIN visits ref_v ON v.from_visit = ref_v.id
                LEFT JOIN urls ref_u ON ref_v.url = ref_u.id
                ORDER BY v.visit_time DESC
                LIMIT 1000
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                transition_types = {
                    0: 'Link',
                    1: 'Typed',
                    2: 'Auto Bookmark',
                    3: 'Auto Subframe',
                    4: 'Manual Subframe',
                    5: 'Generated',
                    6: 'Start Page',
                    7: 'Form Submit',
                    8: 'Reload'
                }
                
                for row in results:
                    data.append({
                        'visit_time': self.chrome_to_timestamp(row[0]),
                        'url': row[1] or '',
                        'title': row[2] or '',
                        'transition': transition_types.get(row[3], 'Unknown'),
                        'referrer_url': row[4] or '',
                        'referrer_title': row[5] or '',
                        'segment_name': 'Chrome History'
                    })
                
            elif self.browser_type == 'firefox':
                query = """
                SELECT 
                    hv.visit_date,
                    p.url,
                    p.title,
                    hv.visit_type,
                    ref_p.url as referrer_url,
                    ref_p.title as referrer_title
                FROM moz_historyvisits hv
                JOIN moz_places p ON hv.place_id = p.id
                LEFT JOIN moz_historyvisits ref_hv ON hv.from_visit = ref_hv.id
                LEFT JOIN moz_places ref_p ON ref_hv.place_id = ref_p.id
                ORDER BY hv.visit_date DESC
                LIMIT 1000
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    data.append({
                        'visit_time': self.firefox_to_timestamp(row[0]),
                        'url': row[1] or '',
                        'title': row[2] or '',
                        'transition': f'Type {row[3]}' if row[3] else 'Unknown',
                        'referrer_url': row[4] or '',
                        'referrer_title': row[5] or '',
                        'segment_name': 'Firefox History'
                    })
            
            else:  # Safari and unknown
                data = []
            
            conn.close()
            return data
            
        except Exception as e:
            print(f"Error extracting visits data: {e}")
            return []
    
    def get_search_terms_data(self):
        """Extract search terms data based on browser type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if self.browser_type == 'chrome':
                query = """
                SELECT 
                    kt.last_visit_time,
                    kt.url,
                    kt.term,
                    u.title,
                    u.visit_count
                FROM keyword_search_terms kt
                JOIN urls u ON kt.url_id = u.id
                ORDER BY kt.last_visit_time DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                data = []
                for row in results:
                    data.append({
                        'last_visit_time': self.chrome_to_timestamp(row[0]),
                        'search_url': row[1] or '',
                        'term': row[2] or '',
                        'page_title': row[3] or '',
                        'visit_count': row[4] or 0
                    })
                
            else:  # Firefox, Safari and unknown don't have easy search terms extraction
                data = []
            
            conn.close()
            return data
            
        except Exception as e:
            print(f"Error extracting search terms data: {e}")
            return []

# Global variable to store current parser
current_parser = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_parser
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.lower().endswith('.sqlite'):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Create parser instance
            current_parser = BrowserHistoryParser(filepath)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'browser_type': current_parser.browser_type,
                'message': f'Successfully loaded {current_parser.browser_type.title()} database'
            })
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Please upload a .sqlite file'}), 400

@app.route('/api/history')
def get_history():
    global current_parser
    if not current_parser:
        return jsonify({'error': 'No database loaded'}), 400
    
    try:
        data = current_parser.get_history_data()
        return jsonify({'data': data, 'browser_type': current_parser.browser_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads')
def get_downloads():
    global current_parser
    if not current_parser:
        return jsonify({'error': 'No database loaded'}), 400
    
    try:
        data = current_parser.get_downloads_data()
        return jsonify({'data': data, 'browser_type': current_parser.browser_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/visits')
def get_visits():
    global current_parser
    if not current_parser:
        return jsonify({'error': 'No database loaded'}), 400
    
    try:
        data = current_parser.get_visits_data()
        return jsonify({'data': data, 'browser_type': current_parser.browser_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-terms')
def get_search_terms():
    global current_parser
    if not current_parser:
        return jsonify({'error': 'No database loaded'}), 400
    
    try:
        data = current_parser.get_search_terms_data()
        return jsonify({'data': data, 'browser_type': current_parser.browser_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)