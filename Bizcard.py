import streamlit as st
from streamlit_option_menu import option_menu
import easyocr
from PIL import Image
import pandas as pd
import numpy as np
import re
import io
import mysql.connector
import os
import uuid
import base64


# Function to extract text from image
def image_to_text(path):
    input_img = Image.open(path)
    image_arr = np.array(input_img)
    reader = easyocr.Reader(['en'])
    text = reader.readtext(image_arr, detail=0)
    return text, input_img

# Function to extract relevant information from extracted text
def extracted_text(texts):
    extrd_dict = {"NAME":[], "DESIGNATION":[], "COMPANY_NAME":[], "CONTACT":[], "EMAIL":[], "WEBSITE":[],
                  "ADDRESS":[], "PINCODE":[]}

    extrd_dict["NAME"].append(texts[0])
    extrd_dict["DESIGNATION"].append(texts[1])

    for i in range(2,len(texts)):
        if texts[i].startswith("+") or (texts[i].replace("-","").isdigit() and '-' in texts[i]):
            extrd_dict["CONTACT"].append(texts[i])
        elif "@" in texts[i] and ".com" in texts[i]:
            extrd_dict["EMAIL"].append(texts[i])
        elif "WWW" in texts[i] or "www" in texts[i] or "Www" in texts[i] or "wWw" in texts[i] or "wwW" in texts[i]:
            small= texts[i].lower()
            extrd_dict["WEBSITE"].append(small)
        elif "Tamil Nadu" in texts[i] or "TamilNadu" in texts[i] or texts[i].isdigit():
            extrd_dict["PINCODE"].append(texts[i])
        elif re.match(r'^[A-Za-z]', texts[i]):
            extrd_dict["COMPANY_NAME"].append(texts[i])
        else:
            remove_colon= re.sub(r'[,;]','',texts[i])
            extrd_dict["ADDRESS"].append(remove_colon)

    for key,value in extrd_dict.items():
        if len(value)>0:
            concadenate= " ".join(value)
            extrd_dict[key] = [concadenate]
        else:
            value = "NA"
            extrd_dict[key] = [value]

    return extrd_dict

# Function to connect to MySQL database
def connect_to_mysql():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="tech@123",
        database="bizcardx",
        auth_plugin='mysql_native_password'
    )

# Function to encode image data
def encode_image(image_data):
    return base64.b64encode(image_data).decode('utf-8')

# Function to save image to file system and return the file path
def save_image_to_file_system(image_data):
    # Define the directory where images will be saved
    image_directory = "./images/"
    # Ensure the directory exists, create it if not
    os.makedirs(image_directory, exist_ok=True)
    # Generate a unique filename
    filename = str(uuid.uuid4()) + ".png"
    # Save the image to the directory
    image_path = os.path.join(image_directory, filename)
    with open(image_path, "wb") as f:
        f.write(image_data)
    return image_path

# Streamlit configuration
st.set_page_config(layout="wide")
st.title("EXTRACTING BUSINESS CARD DATA WITH 'OCR'")

# Sidebar menu
with st.sidebar:
    select = option_menu("Main Menu", ["Home", "Upload & Modifying", "Delete"])

# Main body
if select == "Home":
    st.markdown("### :blue[**Technologies Used :**] Python, easy OCR, Streamlit, SQL, Pandas")
    st.write("### :green[**About :**] Bizcard is a Python application designed to extract information from business cards.")
    st.write('### The main purpose of Bizcard is to automate the process of extracting key details from business card images, such as the name, designation, company, contact information, and other relevant data. By leveraging the power of OCR (Optical Character Recognition) provided by EasyOCR, Bizcard is able to extract text from the images.')

elif select == "Upload & Modifying":
    img = st.file_uploader("Upload the Image", type=["png", "jpg", "jpeg"])

    if img is not None:
        st.image(img, width=300)
        text_image, input_img = image_to_text(img)
        text_dict = extracted_text(text_image)

        if text_dict:
            st.success("TEXT IS EXTRACTED SUCCESSFULLY")

        df = pd.DataFrame(text_dict)
        Image_bytes = io.BytesIO()
        input_img.save(Image_bytes, format="PNG")
        image_data = Image_bytes.getvalue()
        data = {"IMAGE": [image_data]}
        df_1 = pd.DataFrame(data)
        concat_df = pd.concat([df,df_1], axis=1)
        st.dataframe(concat_df)
        button_1 = st.button("Save", use_container_width=True)

        if button_1:
            mydb = connect_to_mysql()
            cursor = mydb.cursor()
            create_table_query = '''CREATE TABLE IF NOT EXISTS bizcard_details(name varchar(225),
                                                                                  designation varchar(225),
                                                                                  company_name varchar(225),
                                                                                  contact varchar(225),
                                                                                  email varchar(225),
                                                                                  website text,
                                                                                  address text,
                                                                                  pincode varchar(225),
                                                                                  image varchar(500)
                                                                                  )'''
            cursor.execute(create_table_query)
            mydb.commit()
            insert_query = '''INSERT INTO bizcard_details(name, designation, company_name,contact, email, website, address,
                                                          pincode, image)
                              VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            datas = concat_df.values.tolist()[0]
            image_path = save_image_to_file_system(image_data)
            datas[-1] = image_path
            cursor.execute(insert_query, datas)
            mydb.commit()
            st.success("SAVED SUCCESSFULLY")

    method = st.radio("Select the Method", ["None", "Preview", "Modify"])

    if method == "None":
        st.write("")

    if method == "Preview":
        mydb = connect_to_mysql()
        cursor = mydb.cursor()
        select_query = "SELECT * FROM bizcard_details"
        cursor.execute(select_query)
        table = cursor.fetchall()
        mydb.commit()
        table_df = pd.DataFrame(table, columns=("NAME", "DESIGNATION", "COMPANY_NAME", "CONTACT", "EMAIL", "WEBSITE",
                                                "ADDRESS", "PINCODE", "IMAGE"))
        st.dataframe(table_df)

    elif method == "Modify":
        mydb = connect_to_mysql()
        cursor = mydb.cursor()
        select_query = "SELECT * FROM bizcard_details"
        cursor.execute(select_query)
        table = cursor.fetchall()
        mydb.commit()
        table_df = pd.DataFrame(table, columns=("NAME", "DESIGNATION", "COMPANY_NAME", "CONTACT", "EMAIL", "WEBSITE",
                                                "ADDRESS", "PINCODE", "IMAGE"))
        col1, col2 = st.columns(2)
        with col1:
            selected_name = st.selectbox("Select the name", table_df["NAME"])
        df_3 = table_df[table_df["NAME"] == selected_name]
        df_4 = df_3.copy()
        col1, col2 = st.columns(2)
        with col1:
            mo_name = st.text_input("Name", df_3["NAME"].unique()[0])
            mo_desi = st.text_input("Designation", df_3["DESIGNATION"].unique()[0])
            mo_com_name = st.text_input("Company_name", df_3["COMPANY_NAME"].unique()[0])
            mo_contact = st.text_input("Contact", df_3["CONTACT"].unique()[0])
            mo_email = st.text_input("Email", df_3["EMAIL"].unique()[0])
            df_4["NAME"] = mo_name
            df_4["DESIGNATION"] = mo_desi
            df_4["COMPANY_NAME"] = mo_com_name
            df_4["CONTACT"] = mo_contact
            df_4["EMAIL"] = mo_email
        with col2:
            mo_website = st.text_input("Website", df_3["WEBSITE"].unique()[0])
            mo_addre = st.text_input("Address", df_3["ADDRESS"].unique()[0])
            mo_pincode = st.text_input("Pincode", df_3["PINCODE"].unique()[0])
            mo_image = st.text_input("Image", df_3["IMAGE"].unique()[0])
            df_4["WEBSITE"] = mo_website
            df_4["ADDRESS"] = mo_addre
            df_4["PINCODE"] = mo_pincode
            df_4["IMAGE"] = mo_image
        st.dataframe(df_4)
        col1, col2 = st.columns(2)
        with col1:
            button_3 = st.button("Modify", use_container_width=True)
        if button_3:
            mydb = connect_to_mysql()
            cursor = mydb.cursor()
            cursor.execute(f"DELETE FROM bizcard_details WHERE NAME = '{selected_name}'")
            mydb.commit()
            insert_query = '''INSERT INTO bizcard_details(name, designation, company_name,contact, email, website, address,
                                                          pincode, image)
                              VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            datas = df_4.values.tolist()[0]
            cursor.execute(insert_query, datas)
            mydb.commit()
            st.success("MODIFIED SUCCESSFULLY")

elif select == "Delete":
    mydb = connect_to_mysql()
    cursor = mydb.cursor()
    col1, col2 = st.columns(2)
    with col1:
        select_query = "SELECT NAME FROM bizcard_details"
        cursor.execute(select_query)
        table1 = cursor.fetchall()
        mydb.commit()
        names = []
        for i in table1:
            names.append(i[0])
        name_select = st.selectbox("Select the name", names)
    with col2:
        select_query = f"SELECT DESIGNATION FROM bizcard_details WHERE NAME ='{name_select}'"
        cursor.execute(select_query)
        table2 = cursor.fetchall()
        mydb.commit()
        designations = []
        for j in table2:
            designations.append(j[0])
        designation_select = st.selectbox("Select the designation", options=designations)
    if name_select and designation_select:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"Selected Name : {name_select}")
            st.write("")
            st.write("")
            st.write("")
            st.write(f"Selected Designation : {designation_select}")
        with col2:
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            remove = st.button("Delete", use_container_width=True)
            if remove:
                cursor.execute(f"DELETE FROM bizcard_details WHERE NAME ='{name_select}' AND DESIGNATION = '{designation_select}'")
                mydb.commit()
                st.warning("DELETED")
