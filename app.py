
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import secrets


DB_PATH = Path('ehealth.db')
ROLES = ['Subscriber', 'Facility Admin', 'System Admin']


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def query_df(sql, params=()):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def execute(sql, params=()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200_000).hex()
    return f'{salt}${digest}'


def verify_password(password, stored):
    try:
        salt, expected = stored.split('$', 1)
        actual = hash_password(password, salt).split('$', 1)[1]
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.executescript('''CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE, city TEXT NOT NULL, area TEXT,
            emergency_contact TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, type TEXT NOT NULL,
            city TEXT NOT NULL, area TEXT NOT NULL, address TEXT, phone TEXT,
            latitude REAL, longitude REAL, opening_hours TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT, facility_id INTEGER NOT NULL,
            full_name TEXT NOT NULL, role TEXT NOT NULL, specialization TEXT, phone TEXT,
            FOREIGN KEY(facility_id) REFERENCES facilities(id)
        );
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT, facility_id INTEGER NOT NULL,
            service_name TEXT NOT NULL, description TEXT, available TEXT NOT NULL DEFAULT 'Yes',
            FOREIGN KEY(facility_id) REFERENCES facilities(id)
        );
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT, facility_id INTEGER NOT NULL,
            medicine_name TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0,
            price REAL DEFAULT 0, available TEXT NOT NULL DEFAULT 'Yes',
            FOREIGN KEY(facility_id) REFERENCES facilities(id)
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, subscriber_id INTEGER NOT NULL,
            facility_id INTEGER NOT NULL, appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL, reason TEXT, status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(subscriber_id) REFERENCES subscribers(id),
            FOREIGN KEY(facility_id) REFERENCES facilities(id)
        );
        CREATE TABLE IF NOT EXISTS health_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, subscriber_id INTEGER NOT NULL,
            reading_type TEXT NOT NULL, systolic INTEGER, diastolic INTEGER,
            sugar_level REAL, notes TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(subscriber_id) REFERENCES subscribers(id)
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Subscriber','Facility Admin','System Admin')),
            subscriber_id INTEGER,
            facility_id INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(subscriber_id) REFERENCES subscribers(id),
            FOREIGN KEY(facility_id) REFERENCES facilities(id)
        );

CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            license_number TEXT,
            appointment_duration INTEGER NOT NULL DEFAULT 30,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(facility_id) REFERENCES facilities(id)
        );

        CREATE TABLE IF NOT EXISTS doctor_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY(doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS doctor_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            subscriber_id INTEGER NOT NULL,
            facility_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(doctor_id) REFERENCES doctors(id),
            FOREIGN KEY(subscriber_id) REFERENCES subscribers(id),
            FOREIGN KEY(facility_id) REFERENCES facilities(id),

            UNIQUE(doctor_id, appointment_date, appointment_time)
        );''')
        conn.commit()
        seed_data(conn)


def seed_data(conn):
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM facilities')
    if cur.fetchone()[0] > 0:
        return
    now = datetime.now().isoformat(timespec='seconds')
    facilities = [
        ('Connaught Hospital','Health Center','Freetown','Central','Lightfoot Boston Street','+232000000001',8.484,-13.234,'24/7',now),
        ('Lumley Community Clinic','Health Center','Freetown','Lumley','Lumley Road','+232000000002',8.466,-13.285,'8am - 8pm',now),
        ('WellCare Pharmacy','Pharmacy','Freetown','Congo Cross','Main Road','+232000000003',8.47,-13.25,'8am - 10pm',now),
        ('MedPlus Pharmacy','Pharmacy','Freetown','Kissy','Kissy Road','+232000000004',8.49,-13.18,'8am - 9pm',now),
    ]
    cur.executemany('INSERT INTO facilities (name,type,city,area,address,phone,latitude,longitude,opening_hours,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)', facilities)
    cur.executemany('INSERT INTO services (facility_id,service_name,description,available) VALUES (?,?,?,?)', [
        (1,'Emergency Care','Urgent care and emergency treatment','Yes'),(1,'Blood Pressure Check','BP screening and advice','Yes'),
        (2,'General Consultation','Doctor consultation','Yes'),(2,'Malaria Test','Rapid malaria test','Yes'),
        (3,'Medicine Sales','Prescription and OTC medicines','Yes'),(4,'Diabetes Supplies','Glucose strips and diabetes support','Yes')])
    cur.executemany('INSERT INTO medicines (facility_id,medicine_name,quantity,price,available) VALUES (?,?,?,?,?)', [
        (3,'Paracetamol',120,2.5,'Yes'),(3,'Amoxicillin',40,7.0,'Yes'),(3,'ORS',80,1.5,'Yes'),
        (4,'Metformin',35,5.0,'Yes'),(4,'Insulin',10,25.0,'Yes'),(4,'Glucose Test Strips',50,15.0,'Yes')])
    cur.executemany('INSERT INTO staff (facility_id,full_name,role,specialization,phone) VALUES (?,?,?,?,?)', [
        (1,'Dr. Mariama Kamara','Doctor','Emergency Medicine','+232111111111'),
        (2,'Dr. Ibrahim Bangura','Doctor','General Medicine','+232222222222'),
        (3,'Fatmata Sesay','Pharmacist','Dispensing','+232333333333'),
        (4,'Mohamed Conteh','Pharmacist','Diabetes Medication','+232444444444')])
    conn.commit()


def get_user(phone):
    df = query_df('SELECT * FROM users WHERE phone=? AND active=1', (phone.strip(),))
    return None if df.empty else df.iloc[0].to_dict()


def get_subscriber(user):
    if not user or not user.get('subscriber_id'):
        return None
    df = query_df('SELECT * FROM subscribers WHERE id=?', (int(user['subscriber_id']),))
    return None if df.empty else df.iloc[0].to_dict()
    

def register_subscriber(full_name, phone, password, city, area, emergency_contact):
    now = datetime.now().isoformat(timespec='seconds')
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO subscribers (full_name,phone,city,area,emergency_contact,created_at) VALUES (?,?,?,?,?,?)',
                    (full_name,phone,city,area,emergency_contact,now))
        subscriber_id = cur.lastrowid
        cur.execute('INSERT INTO users (full_name,phone,password_hash,role,subscriber_id,created_at) VALUES (?,?,?,?,?,?)',
                    (full_name,phone,hash_password(password),'Subscriber',subscriber_id,now))
        conn.commit()


def bootstrap_admin():
    return query_df("SELECT COUNT(*) AS n FROM users WHERE role='System Admin'").iloc[0]['n'] == 0

def doctor_management():
    st.subheader("👨🏾‍⚕️ Doctor Management")
    st.caption("Register doctors and assign them to health centers.")

    health_centers = query_df("""
        SELECT id, name
        FROM facilities
        WHERE type = 'Health Center'
        ORDER BY name
    """)

    if health_centers.empty:
        st.warning("No health centers are registered.")
        return

    st.markdown("### Add Doctor")

    with st.form("add_doctor_form"):
        facility_name = st.selectbox(
            "Health Center",
            health_centers["name"].tolist()
        )

        full_name = st.text_input(
            "Doctor's full name",
            placeholder="e.g. Dr. Mohamed Kamara"
        )

        specialty = st.selectbox(
            "Specialty",
            [
                "General Medicine",
                "Emergency Medicine",
                "Cardiology",
                "Pediatrics",
                "Obstetrics & Gynecology",
                "Surgery",
                "Internal Medicine",
                "Dermatology",
                "Ophthalmology",
                "ENT",
                "Dentistry",
                "Psychiatry",
                "Orthopedics",
                "Neurology",
                "Other"
            ]
        )

        col1, col2 = st.columns(2)

        with col1:
            phone = st.text_input("Phone", placeholder="+232...")
            license_number = st.text_input("License Number")

        with col2:
            email = st.text_input("Email")

            appointment_duration = st.selectbox(
                "Appointment Duration",
                [15, 20, 30, 45, 60],
                index=2,
                format_func=lambda x: f"{x} minutes"
            )

        submitted = st.form_submit_button(
            "Add Doctor",
            use_container_width=True
        )

        if submitted:
            if not full_name.strip():
                st.error("Doctor's name is required.")
            else:
                facility_id = int(
                    health_centers.loc[
                        health_centers["name"] == facility_name,
                        "id"
                    ].iloc[0]
                )

                execute("""
                    INSERT INTO doctors (
                        facility_id,
                        full_name,
                        specialty,
                        phone,
                        email,
                        license_number,
                        appointment_duration,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    facility_id,
                    full_name.strip(),
                    specialty,
                    phone.strip(),
                    email.strip(),
                    license_number.strip(),
                    appointment_duration
                ))

                st.success(
                    f"{full_name} was successfully added to {facility_name}."
                )
                st.rerun()

    st.divider()
    st.markdown("### Registered Doctors")

    doctors = query_df("""
        SELECT
            d.id,
            d.full_name AS doctor,
            d.specialty,
            f.name AS health_center,
            d.phone,
            d.email,
            d.license_number,
            d.appointment_duration,
            CASE
                WHEN d.active = 1 THEN 'Active'
                ELSE 'Inactive'
            END AS status
        FROM doctors d
        JOIN facilities f ON d.facility_id = f.id
        ORDER BY f.name, d.full_name
    """)

    if doctors.empty:
        st.info("No doctors have been registered yet.")
    else:
        st.dataframe(
            doctors,
            use_container_width=True,
            hide_index=True
        )


def doctor_schedule_management():
    st.subheader("📅 Doctor Schedule Management")
    st.caption("Assign working days and hours to registered doctors.")

    doctors = query_df("""
        SELECT d.id, d.full_name, f.name AS facility
        FROM doctors d
        JOIN facilities f ON d.facility_id = f.id
        WHERE d.active = 1
        ORDER BY d.full_name
    """)

    if doctors.empty:
        st.warning("Please register a doctor first.")
        return

    doctor_options = {
        f"{row['full_name']} - {row['facility']}": int(row["id"])
        for _, row in doctors.iterrows()
    }

    with st.form("doctor_schedule_form"):
        selected_doctor = st.selectbox(
            "Select Doctor", list(doctor_options.keys())
        )

        day = st.selectbox(
            "Working Day",
            ["Monday", "Tuesday", "Wednesday",
             "Thursday", "Friday", "Saturday", "Sunday"]
        )

        start_time = st.time_input("Start Time")
        end_time = st.time_input("End Time")

        submitted = st.form_submit_button("Save Schedule")

        if submitted:
            if start_time >= end_time:
                st.error("End time must be later than start time.")
            else:
                doctor_id = doctor_options[selected_doctor]

                execute("""
                    INSERT INTO doctor_schedules
                    (doctor_id, day_of_week, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                """, (
                    doctor_id,
                    day,
                    start_time.strftime("%H:%M"),
                    end_time.strftime("%H:%M")
                ))

                st.success("Doctor schedule saved successfully!")

    st.divider()
    st.markdown("### Registered Doctor Schedules")

    schedules = query_df("""
        SELECT
            d.full_name AS Doctor,
            f.name AS Facility,
            s.day_of_week AS Day,
            s.start_time AS Start,
            s.end_time AS End
        FROM doctor_schedules s
        JOIN doctors d ON s.doctor_id = d.id
        JOIN facilities f ON d.facility_id = f.id
        ORDER BY d.full_name, s.day_of_week
    """)

    if schedules.empty:
        st.info("No doctor schedules have been created yet.")
    else:
        st.dataframe(
            schedules,
            use_container_width=True,
            hide_index=True
        )

init_db()
st.set_page_config(page_title='Edson-Health', page_icon='🏥', layout='wide')

if 'user' not in st.session_state:
    st.session_state.user = None

st.markdown('''<style>
.block-container{padding-top:1.6rem;max-width:1250px}.hero{padding:1.2rem 1.4rem;border:1px solid #ddd;border-radius:16px;margin-bottom:1rem}
.small{opacity:.75;font-size:.9rem}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.title('🏥 E-Health')
    if st.session_state.user:
        u = st.session_state.user
        st.success(f"{u['full_name']}")
        st.caption(u['role'])
        if st.button('Log out', use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        mode = st.radio('Account', ['Login','Create subscriber account'], horizontal=True)
        if mode == 'Login':
            login_phone = st.text_input('Phone number', key='login_phone')
            login_password = st.text_input('Password', type='password', key='login_password')
            if st.button('Login', type='primary', use_container_width=True):
                user = get_user(login_phone)
                if user and verify_password(login_password, user['password_hash']):
                    st.session_state.user = user
                    st.rerun()
                st.error('Invalid phone number or password.')
        else:
            with st.form('subscriber_registration'):
                full_name = st.text_input('Full name')
                new_phone = st.text_input('Phone number')
                password = st.text_input('Password', type='password')
                confirm = st.text_input('Confirm password', type='password')
                city = st.text_input('City', value='Freetown')
                area = st.text_input('Area / Community')
                emergency_contact = st.text_input('Emergency contact')
                submitted = st.form_submit_button('Create account', type='primary', use_container_width=True)
                if submitted:
                    if not full_name or not new_phone or not city or len(password) < 8:
                        st.error('Name, phone and city are required. Password must be at least 8 characters.')
                    elif password != confirm:
                        st.error('Passwords do not match.')
                    else:
                        try:
                            register_subscriber(full_name.strip(),new_phone.strip(),password,city.strip(),area.strip(),emergency_contact.strip())
                            st.success('Account created. You can now log in.')
                        except sqlite3.IntegrityError:
                            st.error('That phone number is already registered.')

        if bootstrap_admin() and bool(os.environ.get("ADMIN_SETUP_KEY") or st.secrets.get("ADMIN_SETUP_KEY")):
            with st.expander('First-time system setup'):
                st.caption('Create the first System Admin. This option disappears after an admin exists.')
                with st.form('bootstrap_admin'): 
                    setup_key = st.text_input(
                           'Administrator setup key', 
                           type='password'
                        )
                    a_name = st.text_input('Admin name')
                    a_phone = st.text_input('Admin phone')
                    a_password = st.text_input(
                          'Admin password', 
                           type='password'
                        )
            if st.form_submit_button('Create System Admin'):
                    if setup_key != (os.environ.get("ADMIN_SETUP_KEY") or st.secrets.get("ADMIN_SETUP_KEY")):
                        st.error("Invalid administrator setup key.")
                    elif a_name and a_phone and len(a_password) >= 10:
                        try:
                            execute(
                                'INSERT INTO users (full_name,phone,password_hash,role,created_at) VALUES (?,?,?,?,?)',
                                (
                                    a_name.strip(),
                                    a_phone.strip(),
                                    hash_password(a_password),
                                    'System Admin',
                                    datetime.now().isoformat(timespec='seconds')
                                )
                            )
                            st.success('System Admin created. Log in above.')
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error('Phone number already exists.')
                    else:
                        st.error('Use a name, phone number, and password of at least 10 characters.')

                
                            
user = st.session_state.user
subscriber = get_subscriber(user)
role = user['role'] if user else 'Guest'

st.markdown('''<div class="hero"><h1>Healthcare access, in one place.</h1>
<p>Find care, check medicine availability, manage appointments and keep your personal health readings together.</p></div>''', unsafe_allow_html=True)

if user:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Signed in as', role)
    c2.metric('Health centers', int(query_df("SELECT COUNT(*) n FROM facilities WHERE type='Health Center'").iloc[0]['n']))
    c3.metric('Pharmacies', int(query_df("SELECT COUNT(*) n FROM facilities WHERE type='Pharmacy'").iloc[0]['n']))
    if subscriber:
        c4.metric('My appointments', int(query_df('SELECT COUNT(*) n FROM appointments WHERE subscriber_id=?',(subscriber['id'],)).iloc[0]['n']))
    else:
        c4.metric('System users', int(query_df('SELECT COUNT(*) n FROM users').iloc[0]['n']))
else:
    st.info('You can search for care and medicines as a guest. Log in to book appointments or manage private health information.')

pages = ['Find Care', 'Pharmacy Medicines']

if role == 'Subscriber':
    pages += ['My Appointments', 'My Health']

if role == 'Facility Admin':
    pages += ['Facility Dashboard']

if role == 'System Admin':
    pages += [
        'Doctor Management',
        'Doctor Schedules',
        'Admin Dashboard'
    ]

page = st.radio(
    'Navigation',
    pages,
    horizontal=True,
    label_visibility='collapsed'
)

st.divider()

if page == 'Find Care':
    st.subheader('🔎 Find Care')
    c1,c2,c3 = st.columns(3)
    city_filter = c1.text_input('City', value=subscriber['city'] if subscriber else 'Freetown', key='care_city')
    area_filter = c2.text_input('Area / Community', key='care_area')
    facility_type = c3.selectbox('Facility Type',['All','Health Center','Pharmacy'], key='care_type')
    sql = 'SELECT name,type,city,area,address,phone,opening_hours,latitude,longitude FROM facilities WHERE city LIKE ?'
    params=[f'%{city_filter}%']
    if area_filter: sql += ' AND area LIKE ?'; params.append(f'%{area_filter}%')
    if facility_type != 'All': sql += ' AND type=?'; params.append(facility_type)
    facilities = query_df(sql+' ORDER BY area,name',params)
    st.dataframe(facilities.drop(columns=['latitude','longitude']),use_container_width=True,hide_index=True)
    map_df = facilities.dropna(subset=['latitude','longitude']).rename(columns={'latitude':'lat','longitude':'lon'})
    if not map_df.empty:
        st.markdown('#### Facility map')
        st.map(map_df[['lat','lon']])
    st.markdown('#### 🚨 Emergency care')
    emergency=query_df("""SELECT f.name,f.phone,f.address,f.opening_hours FROM facilities f JOIN services s ON f.id=s.facility_id WHERE s.service_name LIKE '%Emergency%' AND s.available='Yes'""")
    st.dataframe(emergency,use_container_width=True,hide_index=True)
    st.caption('For a life-threatening emergency, contact local emergency services or go to the nearest emergency facility. This app does not diagnose emergencies.')

elif page == 'Pharmacy Medicines':
    st.subheader('💊 Medicine Availability')
    med_search=st.text_input('Search medicine',placeholder='Paracetamol, Metformin, Insulin…',key='medicine_search')
    sql="""SELECT m.medicine_name,m.quantity,m.price,m.available,f.name AS pharmacy,f.area,f.phone,f.opening_hours FROM medicines m JOIN facilities f ON m.facility_id=f.id WHERE f.type='Pharmacy'"""
    params=[]
    if med_search: sql+=' AND m.medicine_name LIKE ?'; params.append(f'%{med_search}%')
    st.dataframe(query_df(sql+' ORDER BY m.medicine_name',params),use_container_width=True,hide_index=True)
    st.caption('Inventory can change quickly. Confirm availability with the pharmacy before traveling.')

elif page == 'My Appointments':
    st.subheader('📅 My Appointments')
    centers=query_df("SELECT id,name || ' — ' || area AS label FROM facilities WHERE type='Health Center' ORDER BY name")
    with st.form('appointment_form'):
        selected=st.selectbox('Health center',centers['label'].tolist()) if not centers.empty else None
        appt_date=st.date_input('Date',min_value=date.today())
        appt_time=st.time_input('Time')
        reason=st.text_area('Reason for appointment')
        if st.form_submit_button('Request appointment',type='primary') and selected:
            facility_id=int(centers[centers['label']==selected]['id'].iloc[0])
            execute("INSERT INTO appointments (subscriber_id,facility_id,appointment_date,appointment_time,reason,status,created_at) VALUES (?,?,?,?,?,'Pending',?)",
                    (subscriber['id'],facility_id,str(appt_date),str(appt_time),reason,datetime.now().isoformat(timespec='seconds')))
            st.success('Appointment request sent. Status: Pending')
    st.dataframe(query_df("""SELECT a.appointment_date,a.appointment_time,f.name AS facility,a.reason,a.status FROM appointments a JOIN facilities f ON a.facility_id=f.id WHERE a.subscriber_id=? ORDER BY a.appointment_date DESC""",(subscriber['id'],)),use_container_width=True,hide_index=True)

elif page == 'My Health':
    st.subheader('❤️ Private Health Dashboard')
    reading_type=st.selectbox('Reading type',['Blood Pressure','Blood Sugar'])
    with st.form('health_reading_form'):
        if reading_type=='Blood Pressure':
            c1,c2=st.columns(2); systolic=c1.number_input('Systolic',50,250,120); diastolic=c2.number_input('Diastolic',30,160,80); sugar=None
        else:
            systolic=diastolic=None; sugar=st.number_input('Blood sugar level',0.0,600.0,90.0)
        notes=st.text_area('Notes')
        if st.form_submit_button('Save reading'):
            execute('INSERT INTO health_readings (subscriber_id,reading_type,systolic,diastolic,sugar_level,notes,created_at) VALUES (?,?,?,?,?,?,?)',
                    (subscriber['id'],reading_type,systolic,diastolic,sugar,notes,datetime.now().isoformat(timespec='seconds')))
            st.success('Reading saved to your private profile.')
    readings=query_df('SELECT created_at,reading_type,systolic,diastolic,sugar_level,notes FROM health_readings WHERE subscriber_id=? ORDER BY created_at DESC',(subscriber['id'],))
    st.dataframe(readings,use_container_width=True,hide_index=True)
    st.info('These entries are for tracking only and are not a diagnosis. Device integration should use validated medical devices and professional clinical review.')

elif page == 'Facility Dashboard':
    fid=user.get('facility_id')
    if not fid:
        st.warning('This Facility Admin account is not assigned to a facility. Ask a System Admin to assign it.')
    else:
        fac=query_df('SELECT * FROM facilities WHERE id=?',(int(fid),))
        st.subheader(f"🏢 {fac.iloc[0]['name'] if not fac.empty else 'Facility Dashboard'}")
        st.markdown('#### Appointment requests')
        appts=query_df("""SELECT a.id,s.full_name,a.appointment_date,a.appointment_time,a.reason,a.status FROM appointments a JOIN subscribers s ON a.subscriber_id=s.id WHERE a.facility_id=? ORDER BY a.created_at DESC""",(int(fid),))
        st.dataframe(appts,use_container_width=True,hide_index=True)
        if not appts.empty:
            c1,c2=st.columns(2); appt_id=c1.selectbox('Appointment ID',appts['id'].tolist()); status=c2.selectbox('New status',['Pending','Confirmed','Completed','Cancelled'])
            if st.button('Update appointment status'):
                execute('UPDATE appointments SET status=? WHERE id=? AND facility_id=?',(status,int(appt_id),int(fid))); st.success('Appointment updated.'); st.rerun()
        if not fac.empty and fac.iloc[0]['type']=='Pharmacy':
            st.markdown('#### Pharmacy inventory')
            st.dataframe(query_df('SELECT id,medicine_name,quantity,price,available FROM medicines WHERE facility_id=?',(int(fid),)),use_container_width=True,hide_index=True)
            with st.form('add_med'):
                m=st.text_input('Medicine'); q=st.number_input('Quantity',min_value=0); p=st.number_input('Price',min_value=0.0); avail=st.selectbox('Available',['Yes','No'])
                if st.form_submit_button('Add medicine') and m:
                    execute('INSERT INTO medicines (facility_id,medicine_name,quantity,price,available) VALUES (?,?,?,?,?)',(int(fid),m,q,p,avail)); st.success('Medicine added.')

elif page == 'Doctor Management':
    doctor_management()
elif page == 'Doctor Schedules':
    doctor_schedule_management()

elif page == 'Admin Dashboard':
    st.subheader('🛡️ System Admin Dashboard')
    tabs=st.tabs(['Overview','Facilities','Users','Appointments'])
    with tabs[0]:
        a,b,c=st.columns(3); a.metric('Users',int(query_df('SELECT COUNT(*) n FROM users').iloc[0]['n'])); b.metric('Facilities',int(query_df('SELECT COUNT(*) n FROM facilities').iloc[0]['n'])); c.metric('Appointments',int(query_df('SELECT COUNT(*) n FROM appointments').iloc[0]['n']))
    with tabs[1]:
        st.dataframe(query_df('SELECT id,name,type,city,area,phone,opening_hours FROM facilities ORDER BY name'),use_container_width=True,hide_index=True)
        with st.expander('Register a facility'):
            with st.form('facility_form'):
                name=st.text_input('Facility name'); ftype=st.selectbox('Type',['Health Center','Pharmacy']); city=st.text_input('City',value='Freetown'); area=st.text_input('Area'); address=st.text_input('Address'); phone=st.text_input('Phone'); hours=st.text_input('Opening hours',value='8am - 5pm'); lat=st.number_input('Latitude',value=0.0,format='%.6f'); lon=st.number_input('Longitude',value=0.0,format='%.6f')
                if st.form_submit_button('Register facility') and name and city and area:
                    execute('INSERT INTO facilities (name,type,city,area,address,phone,latitude,longitude,opening_hours,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',(name,ftype,city,area,address,phone,lat or None,lon or None,hours,datetime.now().isoformat(timespec='seconds'))); st.success('Facility registered.'); st.rerun()
    with tabs[2]:
        st.dataframe(query_df('SELECT id,full_name,phone,role,facility_id,active,created_at FROM users ORDER BY created_at DESC'),use_container_width=True,hide_index=True)
        st.markdown('#### Create Facility Admin')
        facilities=query_df("SELECT id,name || ' — ' || type AS label FROM facilities ORDER BY name")
        with st.form('facility_admin_form'):
            n=st.text_input('Full name'); p=st.text_input('Phone'); pw=st.text_input('Temporary password',type='password'); flabel=st.selectbox('Assigned facility',facilities['label'].tolist()) if not facilities.empty else None
            if st.form_submit_button('Create Facility Admin') and n and p and flabel and len(pw)>=8:
                fid=int(facilities[facilities['label']==flabel]['id'].iloc[0])
                try:
                    execute('INSERT INTO users (full_name,phone,password_hash,role,facility_id,created_at) VALUES (?,?,?,?,?,?)',(n,p,hash_password(pw),'Facility Admin',fid,datetime.now().isoformat(timespec='seconds'))); st.success('Facility Admin created.'); st.rerun()
                except sqlite3.IntegrityError: st.error('Phone number already exists.')
    with tabs[3]:
        appts=query_df("""SELECT a.id,s.full_name AS subscriber,f.name AS facility,a.appointment_date,a.appointment_time,a.reason,a.status FROM appointments a JOIN subscribers s ON a.subscriber_id=s.id JOIN facilities f ON a.facility_id=f.id ORDER BY a.created_at DESC""")
        st.dataframe(appts,use_container_width=True,hide_index=True)

st.divider()
st.caption('E-Health MVP v2 • Educational prototype — production healthcare deployment requires privacy, security, regulatory, clinical, and operational review.')
