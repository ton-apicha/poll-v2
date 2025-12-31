"""
SuperPoll Database Module
All database operations for campaigns, questions, responses
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "quickpoll.db"

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database with schema"""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_connection() as conn:
        c = conn.cursor()
        
        # Create campaigns table
        c.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create questions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                question_text TEXT NOT NULL,
                question_type TEXT DEFAULT 'single',
                max_selections INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        ''')
        
        # Create options table
        c.execute('''
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                option_text TEXT NOT NULL,
                image_url TEXT,
                bg_color TEXT DEFAULT '#ffffff',
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        ''')
        
        # Create responses table
        c.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                demographic_data TEXT,
                ip_address TEXT,
                user_agent TEXT,
                location_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        ''')
        
        # Create response_details table
        c.execute('''
            CREATE TABLE IF NOT EXISTS response_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER,
                question_id INTEGER,
                option_id INTEGER,
                FOREIGN KEY (response_id) REFERENCES responses(id),
                FOREIGN KEY (question_id) REFERENCES questions(id),
                FOREIGN KEY (option_id) REFERENCES options(id)
            )
        ''')
        
        # Create demographic_attributes table (ตั้งค่าคุณสมบัติ)
        c.execute('''
            CREATE TABLE IF NOT EXISTS demographic_attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                label TEXT NOT NULL,
                input_type TEXT DEFAULT 'select',
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create demographic_options table (ตัวเลือกของแต่ละคุณสมบัติ)
        c.execute('''
            CREATE TABLE IF NOT EXISTS demographic_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attribute_id INTEGER,
                option_text TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (attribute_id) REFERENCES demographic_attributes(id)
            )
        ''')
        
        # Create campaign_demographics table (เชื่อม campaign กับ demographics)
        c.execute('''
            CREATE TABLE IF NOT EXISTS campaign_demographics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                attribute_id INTEGER,
                is_required BOOLEAN DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                FOREIGN KEY (attribute_id) REFERENCES demographic_attributes(id)
            )
        ''')
        
        # Create indexes for performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_responses_campaign ON responses(campaign_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_response_details_response ON response_details(response_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_questions_campaign ON questions(campaign_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_options_question ON options(question_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_demo_options_attr ON demographic_options(attribute_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_campaign_demo ON campaign_demographics(campaign_id)')
        
        # Create images table (Image Manager)
        c.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT,
                file_path TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_images_category ON images(category)')
        
        # Create settings table
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        # Create default settings
        c.execute('SELECT COUNT(*) FROM settings')
        if c.fetchone()[0] == 0:
            create_default_settings(conn)
        
        # Create default demographics if none exists
        c.execute('SELECT COUNT(*) FROM demographic_attributes')
        if c.fetchone()[0] == 0:
            create_default_demographics(conn)
        
        # Create default campaign if none exists
        c.execute('SELECT COUNT(*) FROM campaigns')
        if c.fetchone()[0] == 0:
            create_default_campaign(conn)

def create_default_settings(conn):
    """Create default server settings"""
    c = conn.cursor()
    
    default_settings = [
        ("server_url", "http://localhost:8501", "URL ของ server สำหรับสร้าง QR Code"),
        ("app_name", "SuperPoll", "ชื่อแอปพลิเคชัน"),
        ("admin_password", "superpoll2025", "รหัสผ่านเข้าระบบ Admin"),
    ]
    
    for key, value, desc in default_settings:
        c.execute('''
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
        ''', (key, value, desc))
    
    conn.commit()

def create_default_demographics(conn):
    """Create default demographic attributes"""
    c = conn.cursor()
    
    # Default attributes
    attributes = [
        ("district", "อำเภอ", "select", 1, ["ตะกั่วป่า", "ท้ายเหมือง", "คุระบุรี", "กะปง"]),
        ("area", "พื้นที่", "select", 2, ["ในเขตเทศบาล", "นอกเขตเทศบาล"]),
        ("generation", "ช่วงอายุ (Gen)", "select", 3, ["Gen Z (18-25)", "Gen Y (26-45)", "Gen X (46-60)", "Boomer (61+)"]),
        ("gender", "เพศ", "select", 4, ["ชาย", "หญิง", "อื่นๆ"]),
    ]
    
    for name, label, input_type, order, options in attributes:
        c.execute('''
            INSERT INTO demographic_attributes (name, label, input_type, display_order, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (name, label, input_type, order))
        attr_id = c.lastrowid
        
        for i, opt_text in enumerate(options):
            c.execute('''
                INSERT INTO demographic_options (attribute_id, option_text, display_order)
                VALUES (?, ?, ?)
            ''', (attr_id, opt_text, i))
    
    conn.commit()

def create_default_campaign(conn):
    """Create default campaign with sample question"""
    c = conn.cursor()
    
    # Insert default campaign
    c.execute('''
        INSERT INTO campaigns (title, description, is_active)
        VALUES (?, ?, ?)
    ''', (
        "โพลเลือกตั้ง ส.ส. พังงา เขต 2",
        "สำรวจความคิดเห็นประชาชน N=360",
        1
    ))
    campaign_id = c.lastrowid
    
    # Insert sample question
    c.execute('''
        INSERT INTO questions (campaign_id, question_text, question_type, max_selections, display_order)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        campaign_id,
        "คุณจะเลือกผู้สมัครคนใด?",
        "single",
        1,
        1
    ))
    question_id = c.lastrowid
    
    # Insert sample options
    sample_options = [
        ("ผู้สมัครหมายเลข 1", None, "#3b82f6"),
        ("ผู้สมัครหมายเลข 2", None, "#22c55e"),
        ("ผู้สมัครหมายเลข 3", None, "#f59e0b"),
        ("ยังไม่ตัดสินใจ", None, "#6b7280"),
    ]
    
    for i, (text, img, color) in enumerate(sample_options):
        c.execute('''
            INSERT INTO options (question_id, option_text, image_url, bg_color, display_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (question_id, text, img, color, i))
    
    conn.commit()

# =============================================================================
# Campaign Functions
# =============================================================================

def create_campaign(title: str, description: str = "") -> int:
    """Create a new campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO campaigns (title, description, is_active)
            VALUES (?, ?, 1)
        ''', (title, description))
        conn.commit()
        return c.lastrowid

def get_campaigns():
    """Get all campaigns"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM campaigns ORDER BY created_at DESC')
        return [dict(row) for row in c.fetchall()]

def get_campaign(campaign_id: int):
    """Get single campaign by ID"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        row = c.fetchone()
        return dict(row) if row else None

def update_campaign(campaign_id: int, title: str, description: str):
    """Update campaign details"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE campaigns SET title = ?, description = ?
            WHERE id = ?
        ''', (title, description, campaign_id))
        conn.commit()

def toggle_campaign_status(campaign_id: int):
    """Toggle campaign active status"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE campaigns SET is_active = NOT is_active
            WHERE id = ?
        ''', (campaign_id,))
        conn.commit()

def delete_campaign(campaign_id: int):
    """Delete campaign and all related data"""
    with get_connection() as conn:
        c = conn.cursor()
        # Delete response details
        c.execute('''
            DELETE FROM response_details WHERE response_id IN 
            (SELECT id FROM responses WHERE campaign_id = ?)
        ''', (campaign_id,))
        # Delete responses
        c.execute('DELETE FROM responses WHERE campaign_id = ?', (campaign_id,))
        # Delete options
        c.execute('''
            DELETE FROM options WHERE question_id IN 
            (SELECT id FROM questions WHERE campaign_id = ?)
        ''', (campaign_id,))
        # Delete questions
        c.execute('DELETE FROM questions WHERE campaign_id = ?', (campaign_id,))
        # Delete campaign
        c.execute('DELETE FROM campaigns WHERE id = ?', (campaign_id,))
        conn.commit()

# =============================================================================
# Question Functions
# =============================================================================

def create_question(campaign_id: int, question_text: str, question_type: str,
                    max_selections: int, options: list) -> int:
    """Create a new question with options"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Get next display order
        c.execute('SELECT MAX(display_order) FROM questions WHERE campaign_id = ?', (campaign_id,))
        result = c.fetchone()[0]
        display_order = (result or 0) + 1
        
        # Insert question
        c.execute('''
            INSERT INTO questions (campaign_id, question_text, question_type, max_selections, display_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (campaign_id, question_text, question_type, max_selections, display_order))
        question_id = c.lastrowid
        
        # Insert options
        for i, opt in enumerate(options):
            c.execute('''
                INSERT INTO options (question_id, option_text, image_url, bg_color, display_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (question_id, opt['text'], opt.get('image_url'), opt.get('bg_color', '#ffffff'), i))
        
        conn.commit()
        return question_id

def get_questions(campaign_id: int):
    """Get all questions with options for a campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM questions 
            WHERE campaign_id = ? 
            ORDER BY display_order
        ''', (campaign_id,))
        questions = [dict(row) for row in c.fetchall()]
        
        # Get options for each question
        for q in questions:
            c.execute('''
                SELECT * FROM options 
                WHERE question_id = ? 
                ORDER BY display_order
            ''', (q['id'],))
            q['options'] = [dict(row) for row in c.fetchall()]
        
        return questions

def get_question(question_id: int):
    """Get single question with options"""
    with get_connection() as conn:
        c = conn.cursor()
        
        c.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
        row = c.fetchone()
        if not row:
            return None
        
        question = dict(row)
        
        c.execute('''
            SELECT * FROM options 
            WHERE question_id = ? 
            ORDER BY display_order
        ''', (question_id,))
        question['options'] = [dict(row) for row in c.fetchall()]
        
        return question

def update_question(question_id: int, question_text: str, question_type: str,
                    max_selections: int, options: list):
    """Update question and its options"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Update question
        c.execute('''
            UPDATE questions 
            SET question_text = ?, question_type = ?, max_selections = ?
            WHERE id = ?
        ''', (question_text, question_type, max_selections, question_id))
        
        # Delete old options
        c.execute('DELETE FROM options WHERE question_id = ?', (question_id,))
        
        # Insert new options
        for i, opt in enumerate(options):
            c.execute('''
                INSERT INTO options (question_id, option_text, image_url, bg_color, display_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (question_id, opt['text'], opt.get('image_url'), opt.get('bg_color', '#ffffff'), i))
        
        conn.commit()

def delete_question(question_id: int):
    """Delete question and its options"""
    with get_connection() as conn:
        c = conn.cursor()
        # Delete response details for this question
        c.execute('DELETE FROM response_details WHERE question_id = ?', (question_id,))
        # Delete options
        c.execute('DELETE FROM options WHERE question_id = ?', (question_id,))
        # Delete question
        c.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        conn.commit()

# =============================================================================
# Response Functions
# =============================================================================

def submit_response(campaign_id: int, demographic_data: dict, answers: dict,
                    ip_address: str = None, user_agent: str = None, 
                    location_data: dict = None) -> int:
    """Submit a vote response"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Insert main response
        c.execute('''
            INSERT INTO responses (campaign_id, demographic_data, ip_address, user_agent, location_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            campaign_id,
            json.dumps(demographic_data, ensure_ascii=False),
            ip_address,
            user_agent,
            json.dumps(location_data, ensure_ascii=False) if location_data else None
        ))
        response_id = c.lastrowid
        
        # Insert response details for each question
        for question_id, option_ids in answers.items():
            if isinstance(option_ids, list):
                for opt_id in option_ids:
                    c.execute('''
                        INSERT INTO response_details (response_id, question_id, option_id)
                        VALUES (?, ?, ?)
                    ''', (response_id, question_id, opt_id))
            else:
                c.execute('''
                    INSERT INTO response_details (response_id, question_id, option_id)
                    VALUES (?, ?, ?)
                ''', (response_id, question_id, option_ids))
        
        conn.commit()
        return response_id

def get_response_count(campaign_id: int) -> int:
    """Get total response count for a campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM responses WHERE campaign_id = ?', (campaign_id,))
        return c.fetchone()[0]

def get_voter_logs(campaign_id: int):
    """Get detailed voter logs"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT * FROM responses 
            WHERE campaign_id = ? 
            ORDER BY created_at DESC
        ''', (campaign_id,))
        
        logs = []
        for row in c.fetchall():
            log = dict(row)
            # Parse JSON fields safely
            try:
                log['demographic_data'] = json.loads(log['demographic_data']) if log['demographic_data'] else {}
            except:
                log['demographic_data'] = {}
            try:
                log['location_data'] = json.loads(log['location_data']) if log['location_data'] else {}
            except:
                log['location_data'] = {}
            logs.append(log)
        
        return logs

def reset_responses(campaign_id: int):
    """Delete all responses for a campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            DELETE FROM response_details WHERE response_id IN 
            (SELECT id FROM responses WHERE campaign_id = ?)
        ''', (campaign_id,))
        c.execute('DELETE FROM responses WHERE campaign_id = ?', (campaign_id,))
        conn.commit()

# =============================================================================
# Analytics Functions
# =============================================================================

def get_vote_statistics(campaign_id: int):
    """Get vote statistics for all questions"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Get questions
        c.execute('''
            SELECT * FROM questions 
            WHERE campaign_id = ? 
            ORDER BY display_order
        ''', (campaign_id,))
        questions = [dict(row) for row in c.fetchall()]
        
        result = {'questions': []}
        
        for q in questions:
            # Get options with vote counts
            c.execute('''
                SELECT o.*, COUNT(rd.id) as vote_count
                FROM options o
                LEFT JOIN response_details rd ON o.id = rd.option_id
                WHERE o.question_id = ?
                GROUP BY o.id
                ORDER BY o.display_order
            ''', (q['id'],))
            options = [dict(row) for row in c.fetchall()]
            
            # Calculate total votes for this question
            total_votes = sum(opt['vote_count'] for opt in options)
            
            # Add percentage
            for opt in options:
                opt['percentage'] = (opt['vote_count'] / total_votes * 100) if total_votes > 0 else 0
            
            result['questions'].append({
                'id': q['id'],
                'text': q['question_text'],
                'type': q['question_type'],
                'options': options,
                'total_votes': total_votes
            })
        
        return result

def get_demographic_breakdown(campaign_id: int, field: str):
    """Get breakdown by demographic field"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT demographic_data FROM responses WHERE campaign_id = ?', (campaign_id,))
        
        counts = {}
        total = 0
        
        for row in c.fetchall():
            raw_data = row['demographic_data']
            if not raw_data:
                data = {}
            else:
                try:
                    data = json.loads(raw_data)
                except:
                    data = {}
            
            value = data.get(field, 'ไม่ระบุ')
            counts[value] = counts.get(value, 0) + 1
            total += 1
        
        return {
            'total': total,
            'data': [{'value': k, 'count': v} for k, v in counts.items()]
        }

def get_district_counts(campaign_id: int):
    """Get counts by district (อำเภอ)"""
    return get_demographic_breakdown(campaign_id, 'อำเภอ')

def export_responses_data(campaign_id: int):
    """Export all responses for CSV"""
    with get_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT r.*, GROUP_CONCAT(o.option_text, ' | ') as choices
            FROM responses r
            LEFT JOIN response_details rd ON r.id = rd.response_id
            LEFT JOIN options o ON rd.option_id = o.id
            WHERE r.campaign_id = ?
            GROUP BY r.id
            ORDER BY r.created_at DESC
        ''', (campaign_id,))
        
        results = []
        for row in c.fetchall():
            data = dict(row)
            # Parse demographics
            try:
                demo = json.loads(data['demographic_data']) if data['demographic_data'] else {}
            except:
                demo = {}
            # Parse location
            try:
                loc = json.loads(data['location_data']) if data['location_data'] else {}
            except:
                loc = {}
            
            results.append({
                'id': data['id'],
                'เวลา': data['created_at'],
                'อำเภอ': demo.get('อำเภอ', ''),
                'พื้นที่': demo.get('พื้นที่', ''),
                'Gen': demo.get('Gen', ''),
                'เพศ': demo.get('เพศ', ''),
                'ตัวเลือก': data['choices'],
                'IP': data['ip_address'],
                'เมือง': loc.get('city', ''),
                'ประเทศ': loc.get('country', ''),
                'ISP': loc.get('isp', ''),
            })
        
        return results

# =============================================================================
# Demographic Attributes Functions
# =============================================================================

def get_demographic_attributes(active_only: bool = False):
    """Get all demographic attributes with options"""
    with get_connection() as conn:
        c = conn.cursor()
        
        if active_only:
            c.execute('SELECT * FROM demographic_attributes WHERE is_active = 1 ORDER BY display_order')
        else:
            c.execute('SELECT * FROM demographic_attributes ORDER BY display_order')
        
        attributes = [dict(row) for row in c.fetchall()]
        
        # Get options for each attribute
        for attr in attributes:
            c.execute('''
                SELECT * FROM demographic_options 
                WHERE attribute_id = ? 
                ORDER BY display_order
            ''', (attr['id'],))
            attr['options'] = [dict(row) for row in c.fetchall()]
        
        return attributes

def get_demographic_attribute(attr_id: int):
    """Get single demographic attribute with options"""
    with get_connection() as conn:
        c = conn.cursor()
        
        c.execute('SELECT * FROM demographic_attributes WHERE id = ?', (attr_id,))
        row = c.fetchone()
        if not row:
            return None
        
        attr = dict(row)
        
        c.execute('''
            SELECT * FROM demographic_options 
            WHERE attribute_id = ? 
            ORDER BY display_order
        ''', (attr_id,))
        attr['options'] = [dict(row) for row in c.fetchall()]
        
        return attr

def create_demographic_attribute(name: str, label: str, input_type: str, options: list) -> int:
    """Create a new demographic attribute"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Get next display order
        c.execute('SELECT MAX(display_order) FROM demographic_attributes')
        result = c.fetchone()[0]
        display_order = (result or 0) + 1
        
        c.execute('''
            INSERT INTO demographic_attributes (name, label, input_type, display_order, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (name, label, input_type, display_order))
        attr_id = c.lastrowid
        
        # Insert options
        for i, opt_text in enumerate(options):
            c.execute('''
                INSERT INTO demographic_options (attribute_id, option_text, display_order)
                VALUES (?, ?, ?)
            ''', (attr_id, opt_text, i))
        
        conn.commit()
        return attr_id

def update_demographic_attribute(attr_id: int, name: str, label: str, input_type: str, options: list):
    """Update demographic attribute and its options"""
    with get_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            UPDATE demographic_attributes 
            SET name = ?, label = ?, input_type = ?
            WHERE id = ?
        ''', (name, label, input_type, attr_id))
        
        # Delete old options
        c.execute('DELETE FROM demographic_options WHERE attribute_id = ?', (attr_id,))
        
        # Insert new options
        for i, opt_text in enumerate(options):
            c.execute('''
                INSERT INTO demographic_options (attribute_id, option_text, display_order)
                VALUES (?, ?, ?)
            ''', (attr_id, opt_text, i))
        
        conn.commit()

def toggle_demographic_attribute(attr_id: int):
    """Toggle demographic attribute active status"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE demographic_attributes SET is_active = NOT is_active
            WHERE id = ?
        ''', (attr_id,))
        conn.commit()

def delete_demographic_attribute(attr_id: int):
    """Delete demographic attribute and its options"""
    with get_connection() as conn:
        c = conn.cursor()
        # Delete campaign links
        c.execute('DELETE FROM campaign_demographics WHERE attribute_id = ?', (attr_id,))
        # Delete options
        c.execute('DELETE FROM demographic_options WHERE attribute_id = ?', (attr_id,))
        # Delete attribute
        c.execute('DELETE FROM demographic_attributes WHERE id = ?', (attr_id,))
        conn.commit()

# =============================================================================
# Campaign Demographics Functions
# =============================================================================

def get_campaign_demographics(campaign_id: int):
    """Get demographics assigned to a campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT da.*, cd.is_required, cd.display_order as campaign_order
            FROM demographic_attributes da
            JOIN campaign_demographics cd ON da.id = cd.attribute_id
            WHERE cd.campaign_id = ? AND da.is_active = 1
            ORDER BY cd.display_order
        ''', (campaign_id,))
        
        attributes = [dict(row) for row in c.fetchall()]
        
        # Get options for each attribute
        for attr in attributes:
            c.execute('''
                SELECT * FROM demographic_options 
                WHERE attribute_id = ? 
                ORDER BY display_order
            ''', (attr['id'],))
            attr['options'] = [dict(row) for row in c.fetchall()]
        
        return attributes

def set_campaign_demographics(campaign_id: int, attribute_ids: list, required_map: dict = None):
    """Set demographics for a campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Clear existing
        c.execute('DELETE FROM campaign_demographics WHERE campaign_id = ?', (campaign_id,))
        
        # Insert new
        for i, attr_id in enumerate(attribute_ids):
            is_required = required_map.get(attr_id, True) if required_map else True
            c.execute('''
                INSERT INTO campaign_demographics (campaign_id, attribute_id, is_required, display_order)
                VALUES (?, ?, ?, ?)
            ''', (campaign_id, attr_id, is_required, i))
        
        conn.commit()

def get_campaign_demographic_ids(campaign_id: int):
    """Get list of demographic attribute IDs for a campaign"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT attribute_id FROM campaign_demographics 
            WHERE campaign_id = ? 
            ORDER BY display_order
        ''', (campaign_id,))
        return [row['attribute_id'] for row in c.fetchall()]

# =============================================================================
# Image Manager Functions
# =============================================================================

def get_images(category: str = None):
    """Get all images, optionally filtered by category"""
    with get_connection() as conn:
        c = conn.cursor()
        if category:
            c.execute('SELECT * FROM images WHERE category = ? ORDER BY created_at DESC', (category,))
        else:
            c.execute('SELECT * FROM images ORDER BY created_at DESC')
        return [dict(row) for row in c.fetchall()]

def get_image(image_id: int):
    """Get single image by ID"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM images WHERE id = ?', (image_id,))
        row = c.fetchone()
        return dict(row) if row else None

def add_image(filename: str, original_name: str, file_path: str, category: str = 'general', description: str = '') -> int:
    """Add new image to database"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO images (filename, original_name, file_path, category, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, original_name, file_path, category, description))
        conn.commit()
        return c.lastrowid

def update_image(image_id: int, category: str, description: str):
    """Update image metadata"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE images SET category = ?, description = ?
            WHERE id = ?
        ''', (category, description, image_id))
        conn.commit()

def delete_image(image_id: int):
    """Delete image from database"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT file_path FROM images WHERE id = ?', (image_id,))
        row = c.fetchone()
        if row:
            # Delete file
            file_path = row['file_path']
            try:
                import os
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        c.execute('DELETE FROM images WHERE id = ?', (image_id,))
        conn.commit()

def get_image_categories():
    """Get list of unique categories"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT DISTINCT category FROM images ORDER BY category')
        return [row['category'] for row in c.fetchall()]

# =============================================================================
# Settings Functions
# =============================================================================

def get_all_settings():
    """Get all settings"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM settings ORDER BY key')
        return [dict(row) for row in c.fetchall()]

def get_setting(key: str, default: str = None):
    """Get single setting value by key"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = c.fetchone()
        return row['value'] if row else default

def set_setting(key: str, value: str, description: str = None):
    """Set or update a setting"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM settings WHERE key = ?', (key,))
        if c.fetchone():
            c.execute('''
                UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE key = ?
            ''', (value, key))
        else:
            c.execute('''
                INSERT INTO settings (key, value, description)
                VALUES (?, ?, ?)
            ''', (key, value, description))
        conn.commit()

def delete_setting(key: str):
    """Delete a setting"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM settings WHERE key = ?', (key,))
        conn.commit()
