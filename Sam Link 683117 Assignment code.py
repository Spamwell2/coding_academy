# -*- coding: utf-8 -*-
"""
Created on Wed May 17 12:36:20 2023

@author: sgl_9
"""
import pandas as pd
import anvil.server
import pyodbc
import random
import string
import anvil.media

#published anvil server connection
anvil.server.connect("server_4IRSBXO6EROW6NX4QOHGB5QD-F6Y3KOBGAPC3NXIM")

#developer anvil server connection
#anvil.server.connect("server_I2J7PMLT5KCSNPXS2TFGEK3Z-F6Y3KOBGAPC3NXIM")

"""
#laptop sql connection + filepath
conn = pyodbc.connect('''DRIVER={SQL Server}; 
                            SERVER=LAPTOP-PRCKQJF0\SQLEXPRESS03;
                            DATABASE=FlightDB;
                            Trusted_Connection=yes;''')
                            
path = 'C:\\Users\\sgl_9\\OneDrive\\Coding Academy\\Assignment'

"""

#desktop sql connection + filepath
conn = pyodbc.connect('DRIVER={SQL Server};' 
                            'SERVER=SAM\SQLEXPRESS;'
                            'DATABASE=FlightDB;'
                            'Trusted_Connection=yes;')


path = 'C:\\Users\\Sam\\OneDrive\\Coding Academy\\Assignment'

cursor = conn.cursor()




#checks an entered username and password in user database
#if fields are blank or no match returns false
#if both match checks admin status and returns login value based on result
@anvil.server.callable
def check_user(username, password):
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?',
               (username, password))
    user = cursor.fetchone()
    if not user:
        return False
    login = 0
    if user[2] == 'N':
        login = 1
    elif user[2] == 'Y':
        login = 2
    conn.commit()
    return login
 
#checks an entered username in user database and returns false if a match exists
#otherwise creates a new entry in users table with entered username and password
@anvil.server.callable
def sign_up(username, password):
    cursor.execute('SELECT * FROM users WHERE username = ?',
                   (username))
    user = cursor.fetchone()
    if user:
        return False
    else:
        cursor.execute('''INSERT INTO users (username, password, is_admin)
                       VALUES (?, ?, 'N')''',(username, password))
        conn.commit()
        return True
    
#gets price of ticket from database based on ticket type then
#calculates discount based on quantity of tickets
@anvil.server.callable
def discount(ticket_type, quantity):
    cursor.execute('SELECT price FROM tickets WHERE ticket_type = ?',
                   (ticket_type))
    price = cursor.fetchone()
    if quantity == 2:
        discounted_price = price[0] * 0.9
    elif quantity == 3:
        discounted_price = price[0] * 0.8
    elif quantity == 4:
        discounted_price = price[0] * 0.7
    elif quantity >= 5:
        discounted_price = price[0] * 0.6
    else:
        discounted_price = price[0]
    conn.commit()
    return discounted_price

    
#checks and returns ticket availability based on ticket type selected
@anvil.server.callable
def availability(ticket_type):
   cursor.execute('SELECT availability FROM tickets WHERE ticket_type = ?',
                  (ticket_type))
   avail = cursor.fetchone()
   conn.commit()
   return avail[0]

#checks and returns ticket price based on ticket type selected   
@anvil.server.callable
def price_update(ticket_type):
    cursor.execute('SELECT price FROM tickets WHERE ticket_type = ?',
                   (ticket_type))
    price = cursor.fetchone()
    conn.commit()
    return price[0]


#generates a random string to use as a booking reference
#checks to make sure generated string does not already exist in database
#if string exists, re-generates a new string until it is unique
#when a unique string has been generated commits booking details to database
@anvil.server.callable
def buy_ticket(ticket_type, quantity, username, total_paid):
    unique = False
    while unique == False:
        booking_ref = ''.join(random.choice(string.ascii_uppercase) for i in range(8))
        cursor.execute('SELECT * FROM bookings WHERE booking_ref = ?', (booking_ref))
        unique = cursor.fetchone()
        if not unique:
            unique = True         
    cursor.execute('''INSERT INTO bookings (ticket_type, quantity, 
                       username, booking_ref, total_paid)
                       VALUES (?, ?, ?, ?, ?)''', (ticket_type, quantity, 
                       username, booking_ref, total_paid))
    conn.commit()
    return True

 
#updates ticket availability in database based on quantity purchased
@anvil.server.callable
def update_availability(ticket_type, quantity):
    cursor.execute('''UPDATE tickets
                   SET availability = ?
                   WHERE ticket_type = ?''', (quantity, ticket_type))
    conn.commit()
    return


#returns a list of all booking data associated with the current user
#creates a dataframe with that data and converts to csv for later download
@anvil.server.callable
def booking_info(*inputs):
    if len(inputs) == 0:
        cursor.execute('SELECT * FROM bookings')
    else: 
        cursor.execute('''SELECT * FROM bookings WHERE username = ? 
                       OR booking_ref = ?''', (inputs[0], inputs[0]))
    bookings = cursor.fetchall()
    booking_list = [list(i) for i in bookings]
    cols = ['Ticket Type', 'Quantity', 'Username', 'Booking Ref', 'Total Paid']
    bookings_df = pd.DataFrame(booking_list, columns=cols)
    report_df = bookings_df.drop(columns=['Username'])
    report_df.to_csv(path + 'report.csv', index=False)
    conn.commit()
    return booking_list


#checks for a valid booking reference
#if valid, adds the tickets back into available tickets
#then deletes booking details from database
@anvil.server.callable
def cancel_ticket(username, booking_ref):
    if len(booking_ref) < 8:
        return False
    else:
        cursor.execute('''SELECT ticket_type, quantity FROM bookings WHERE username = ? AND
                       booking_ref = ?;''', (username, booking_ref))
        booking = cursor.fetchone()
        if not booking:
            conn.commit()
            return False
        else:
            cursor.execute('''UPDATE tickets
                           SET availability = availability + ?
                           WHERE ticket_type = ?;''', (booking[1], booking[0]))
            conn.commit()
            cursor.execute('''DELETE from bookings WHERE username = ? AND
                           booking_ref = ?;''', (username, booking_ref))
            conn.commit()
            return True


#checks booking reference exists in database if one is entered
#converts booking reference to upper case (purely for visual continuity)
#inserts user feedback into database
@anvil.server.callable
def user_feedback(feedback, booking_ref, username):
    cursor.execute('''SELECT booking_ref FROM bookings WHERE username = ? AND
                   booking_ref = ?''', (username, booking_ref))
    check_booking = cursor.fetchone()
    booking_ref = booking_ref.upper()
    if len(booking_ref) > 0 and not check_booking:
        conn.commit()
        return False
    else:
        cursor.execute('''INSERT INTO feedback (username, booking_ref, user_feedback)
                       VALUES (?, ?, ?)''', (username, booking_ref, feedback))
        conn.commit()
        return True


#if no inputs retrieves the entire data from feedback
#if function called by a user retrieves feedback data relevant to that user
#if function called by admin and a username or booking reference is input, 
#retrieves the relevant data that matches either one
@anvil.server.callable
def get_user_feedback(*inputs):
    if len(inputs) == 0:
        cursor.execute('SELECT ID, booking_ref, user_feedback, response FROM feedback')
    else:
        if inputs[1] == 1:
            cursor.execute('''SELECT ID, booking_ref, user_feedback, response FROM feedback
                           WHERE username = ? OR booking_ref = ?''', inputs[0], inputs[0])
        elif inputs[1] == 2:
            try:
                cursor.execute('''SELECT ID, booking_ref, user_feedback, response FROM feedback
                               WHERE ID = ?''', inputs[0])
            except:
                cursor.execute('''SELECT ID, booking_ref, user_feedback, response FROM feedback
                               WHERE booking_ref = ?''', inputs[0])               
    updated_user_feedback = cursor.fetchall()
    feedback_list = [list(i) for i in updated_user_feedback]
    cols = ['ID', 'Booking Ref', 'User Feedback', 'Admin Response']
    feedback_df = pd.DataFrame(feedback_list, columns=cols)
    feedback_df.to_csv(path + 'report.csv', index=False)
    conn.commit()
    return feedback_list


#updates feedback table with admin response, first checking for a matching ID
#then if this fails, checking for a matching booking reference
@anvil.server.callable
def admin_response(response, reference):
    try:
        cursor.execute('''UPDATE feedback
                       SET response = ?
                       WHERE ID = ?''', (response, reference))
    except:
        cursor.execute('''UPDATE feedback
                       SET response = ?
                       WHERE booking_ref = ?''', (response, reference))
    conn.commit()
    return

#selects ticket types, quantities and total amounts paid from bookings form
#creates dataframes to calculate the sum of total paid, total quantities,
#total quantites and total income grouped by ticket type
#passes dataframes to a list and returns list to front end
#creates a new dataframe from previous list and converts to csv
@anvil.server.callable
def generate_report():
    cursor.execute('SELECT ticket_type, quantity, total_paid FROM bookings')
    income = cursor.fetchall()
    income = [list(i) for i in income]
    col = ['Ticket Type', 'Quantity', 'Total Paid']
    df = pd.DataFrame(income, columns=col)
    total_income = df['Total Paid'].sum()
    total_tickets = df['Quantity'].sum()
    total_per_type = df.groupby(['Ticket Type'])['Quantity'].sum().reindex(
        ['Economy', 'First Class', 'Business Class'], fill_value=0)
    income_per_type = df.groupby(['Ticket Type'])['Total Paid'].sum().reindex(
        ['Economy', 'First Class', 'Business Class'], fill_value=0)
    report = [total_income, total_tickets, list(total_per_type), list(income_per_type)]
    cols = ['Total Income','Tickets Sold','Economy Tickets Sold','First Class Tickets Sold',
            'Business Class Tickets Sold', 'Economy Income', 'First Class Income', 'Business Class Income']
    report_values = [report[0], report[1], report[2][0], report[2][1], report[2][2], 
                     report[3][0], report[3][1], report[3][2]]
    report_df = pd.DataFrame([report_values], columns=cols)
    conn.commit()
    report_df.to_csv(path + 'report.csv', index=False)
    return report

#download previously generated report csv
@anvil.server.callable
def download_report():
    return anvil.media.from_file(path + 'report.csv')

    

