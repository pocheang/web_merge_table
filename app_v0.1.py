import os
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from reportlab.lib.pagesizes import letter, landscape, A3
from reportlab.platypus import Image
from reportlab.pdfgen import canvas
from datetime import datetime
from io import BytesIO
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.enums import TA_CENTER

# Set custom favicon and page title
st.set_page_config(page_title="Merge table Web App", page_icon="path/logo.jpg")


def split_into_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def max_total_characters(series):
    return series.fillna('').astype(str).apply(len).max()

# Custom CSS to hide Streamlit components
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if 'page' not in st.session_state:
    st.session_state.page = 'home'  # Initial page
if 'filtered_df' not in st.session_state:
    st.session_state.filtered_df = None  # To store filtered DataFrame
if 'column_headers' not in st.session_state:
    st.session_state.column_headers = None  # To store column headers
if 'column_order' not in st.session_state:
    st.session_state.column_order = None  # To store column order

counter = 1

def insert_column(merged_df, position):
    global counter
    new_column_name = f"id{counter}_0"
    new_column_name2 = f"column_{counter}_1"
    new_column_name3 = f"column_{counter}_2"
    merged_df.insert(position, new_column_name3, merged_df.iloc[:, 2])
    merged_df.insert(position, new_column_name2, merged_df.iloc[:, 1])
    merged_df.insert(position, new_column_name, merged_df.iloc[:, 0])
    counter += 1


def add_page_number_with_header(canvas, _, team, image_path,confidential, title):
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.setFont("Helvetica", 12)
    width, _ = A3  # A3 page size

    # Header image position (top of the page)
    image_x = 20  # 20 units from the left margin
    image_y = 750  # 60 units from the top margin
    image_width = 150  # Image width
    image_height = 100  # Image height

    # Draw the header image
    canvas.drawImage(image_path, image_x, image_y, width=image_width, height=image_height)

    canvas.drawString(1050, 800, confidential)

    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString((width / 2)+170, 770, title)

    # Team text position (on the right side)
    team_text_width = stringWidth(team, "Helvetica", 9)
    team_x = width + 230 - team_text_width  # Right margin padding of 10
    team_y = 50  # Adjust y-position for team text

    # Draw the team text
    canvas.setFont("Helvetica", 12)
    canvas.drawString(team_x, team_y, team)

    # Draw the page number text
    canvas.drawCentredString((width / 2) + 200, 20, text)

def home_page():
    st.title("Merge and Convert file from excel to PDF")

    uploaded_dfs = []
    if 'uploaded_dfs' not in st.session_state:
        st.session_state.uploaded_dfs = []
    # Upload files
    uploaded_files = st.file_uploader("Upload your CSV or Excel files", type=['csv', 'xlsm', 'xlsx'], accept_multiple_files=True)

    if uploaded_files:
        st.session_state.uploaded_dfs = []
        for uploaded_file in uploaded_files:
            # Read data based on file type
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            if df.empty:
                st.warning(f"The file {uploaded_file.name} is empty.")
            else:
                uploaded_dfs.append(df)
        # Merge files if more than one
        if len(uploaded_dfs) > 1:
            # Start with the first DataFrame
            merged_df = uploaded_dfs[0]
            key_column = merged_df.columns[0]

            # Ensure the key column is string in the first DataFrame
            merged_df[key_column] = merged_df[key_column].astype(str)

            # Iteratively merge the DataFrames
            for df in uploaded_dfs[1:]:
                # Ensure the key column exists and is of string type in the current DataFrame
                if key_column not in df.columns:
                    st.error(f"Key column '{key_column}' not found in one of the uploaded files.")
                    continue

                df[key_column] = df[key_column].astype(str)

                # Merge the DataFrames
                merged_df = pd.merge(merged_df, df, on=key_column, how="inner", validate="1:1")

            # Replace 'nan' with empty strings and clean numeric strings
            merged_df = merged_df.replace('nan', '')
            merged_df.iloc[:, 0] = merged_df.iloc[:, 0].astype(str).str.replace(r'\.0$', '', regex=True)

            # Display the merged DataFrame
            st.write("### Merged Data")
            st.write(merged_df)
        else:
            # Single DataFrame case
            merged_df = uploaded_dfs[0].astype(str)
            merged_df = merged_df.replace('nan', '')
            merged_df.iloc[:, 0] = merged_df.iloc[:, 0].astype(str).str.replace(r'\.0$', '', regex=True)

            # Display the uploaded DataFrame
            st.write("### Uploaded Data")
            st.write(merged_df)

        st.sidebar.image("path/logo.jpg", use_container_width=True)  # For sidebar

        # Filter options
        st.sidebar.header("Filter Options")

        # Dynamic filters
        column = 'filter'

        # Filtering logic for a specific column
        if merged_df[column].dtype == 'object':
            filter_value = st.sidebar.selectbox(f"Filter by {column}",
                                                options=['All'] + merged_df[column].unique().tolist())
            filtered_df = merged_df[merged_df[column] == filter_value] if filter_value != 'All' else merged_df
        else:
            min_value, max_value = float(merged_df[column].min()), float(merged_df[column].max())
            filter_range = st.sidebar.slider(f"Filter {column} range:", min_value, max_value, (min_value, max_value))
            filtered_df = merged_df[(merged_df[column] >= filter_range[0]) & (merged_df[column] <= filter_range[1])]

        # Make sure the first row is always included
        filtered_df = pd.concat([merged_df.iloc[[0]], filtered_df]).drop_duplicates().reset_index(drop=True)

        # Save the filtered dataframe to session state
        st.session_state.filtered_df = filtered_df

        if 'r' not in st.session_state or 'filtered_df' not in st.session_state:
            st.session_state.r = 0
            st.session_state.column_order = []

        if st.session_state.column_order == [] or set(st.session_state.column_order) - set(
                st.session_state.filtered_df.columns):
            st.session_state.column_order = st.session_state.filtered_df.columns.tolist()

        if st.session_state.r == 0:
            st.session_state.column_order = st.session_state.filtered_df.columns.tolist()
            st.session_state.r = 1

        st.sidebar.header("Select Columns to Display")
        with st.sidebar.form(key="column_selection_form"):
            selected_columns = st.multiselect(
                "Choose columns to display",
                st.session_state.filtered_df.columns.tolist(),
                default=st.session_state.column_order
            )
            submitted = st.form_submit_button("Apply")


        if submitted:
            st.session_state.column_order = selected_columns
            st.rerun()

        reset_columns = st.sidebar.button("Reset Columns to Default")

        if reset_columns:
            st.session_state.column_order = st.session_state.filtered_df.columns.tolist()
            st.rerun()


        # Display filtered data
        st.write("### Filtered Data")
        if selected_columns:
            filtered_df_to_display = st.session_state.filtered_df[selected_columns]

            # Display using st_aggrid
            gb = GridOptionsBuilder.from_dataframe(filtered_df_to_display)
            gb.configure_default_column(editable=True, sortable=True, resizable=True, hide=False)
            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
            gb.configure_grid_options(domLayout='normal')
            gb.configure_side_bar()
            grid_options = gb.build()

            response = AgGrid(
                filtered_df_to_display,
                gridOptions=grid_options,
                enable_enterprise_modules=False,
                height=500,
                width='100%',
                theme="alpine",
                update_mode=GridUpdateMode.MODEL_CHANGED,
                allow_unsafe_jscode=True
            )

            # Update session_state DataFrame and column order
            if response['data'] is not None:
                st.session_state.filtered_df = pd.DataFrame(response['data'])
            if 'columnState' in response and response['columnState']:
                reordered_columns = [col['colId'] for col in response['columnState'] if 'colId' in col]
                st.session_state.filtered_df = st.session_state.filtered_df[reordered_columns]
                st.session_state.column_order = reordered_columns

            # Download CSV
            # DataFrame
            df = st.session_state.filtered_df

            df = df.fillna(" ")

            df.columns = [col if "Unnamed" not in col else " " for col in df.columns]

            csv_data = df.to_csv(index=False)

            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name='filtered_data.csv',
                mime='text/csv'
            )

            # Export to PDF
            title = st.text_input("Please input a title for the PDF:")
            confidential = st.text_input("Please input a confidential note for the PDF:", value="Confidential")
            team = st.text_input("Please input create date for the PDF:")
            confirm = st.text_input("Please input confirmed by for the PDF: ")
            signature_data = st.text_input("Please input signature data for the PDF:")
            row_page = st.number_input("Please input a number of rows per page:", min_value=1, value=9)
            fontsize = st.number_input("Please input a font size of table for the PDF: ",min_value=0.1, value=8.0)
            col_size = st.number_input("Please input a size of columns per page:", min_value=1, value=80)
            b_col_size = st.number_input("Please input a size of big columns per page:", min_value=1, value=300)
            last_col_size = st.number_input("Please input a size of last columns per page:", min_value=1, value=80)
            note1 = st.text_area("Please input the content note (use '-' to separate paragraphs):", height=200)
            if note1.strip() == "":
                st.warning("The text area cannot be empty!")
                button_disabled = True
            else:
                button_disabled = False

            if st.button("Generate PDF",disabled=button_disabled):
                # output pdf
                pdf_filename = "output.pdf"

                # Create a BytesIO buffer to save the PDF to memory instead of disk
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=landscape(A3), leftMargin=0 * inch,
                                        rightMargin=0 * inch, topMargin=1.2 * inch, bottomMargin= 0.8* inch)

                # create story
                story = []
                styles = getSampleStyleSheet()

                # Logo
                logo_path = 'path/logo.jpg'  # logo location

                new_columns = []

                for i, col in enumerate(st.session_state.filtered_df.columns):
                    if 'Unnamed' in col and i > 0:
                        new_columns.append(new_columns[i - 1])
                    elif 'Others' in col:
                        new_columns.append('Others')
                    else:
                        new_columns.append(col)

                st.session_state.filtered_df.columns = new_columns

                new_header = st.session_state.filtered_df.columns.tolist()
                st.session_state.filtered_df.loc[-1] = new_header
                st.session_state.filtered_df.index = st.session_state.filtered_df.index.astype(int) + 1

                st.session_state.filtered_df = st.session_state.filtered_df.sort_index()  # sorts the index

                # Define margins and usable width
                left_margin = 0.4 * inch
                right_margin = 0.4 * inch
                usable_width = landscape(A3)[0] - left_margin - right_margin  # Total width minus margins

                long_text_cols = []

                for col_idx in range(st.session_state.filtered_df.shape[1]):
                    cell_values = st.session_state.filtered_df.iloc[2:5, col_idx]

                    if any(len(str(value)) > 45 for value in cell_values):
                        long_text_cols.append(col_idx)

                col_widths = []

                print(long_text_cols)

                if not long_text_cols:
                    long_text_cols.append(-1)

                print(long_text_cols)

                for idx, col in enumerate(st.session_state.filtered_df.columns):
                    if idx in [0, 1, 2]:
                        len_num = 70
                    elif idx == 3:
                        len_num = 120
                    elif idx == long_text_cols or idx in long_text_cols:
                        len_num = b_col_size
                    else:
                        len_num = col_size
                    col_widths.append(len_num)

                print(col_widths)
                # Check if col_widths is empty
                if not col_widths:
                    print("Column widths are empty.")
                    return None  # Early return if column widths are not determined

                # Initialize variables
                total_col_width = 0  # To track the total width of columns on the current page
                max_cols_per_page = 0  # To count the maximum columns per page
                p = 0  # Counter for pages
                max1 = []  # List to store the maximum number of columns per page

                p1 = []
                # Iterate through column widths
                for width in col_widths:
                    total_col_width += width  # Add the current column width to the total

                    # Check if the total width is within the usable width
                    if total_col_width <= usable_width:
                        max_cols_per_page += 1  # Increment the count of columns on the current page
                        p += 1  # Increment the page counter
                    else:
                        # If the width exceeds usable space, finalize the current page
                        max1.append(max_cols_per_page)  # Store the count of columns for the current page

                        p1.append(p)

                            # Insert a column for the current page in the DataFrame
                        insert_column(st.session_state.filtered_df, p)

                            # Prepare for the next page
                        p += 4  # Increment the page counter by 4
                        total_col_width = width + sum(col_widths[:3])  # Reset the total column width
                        max_cols_per_page = 4  # Reset the maximum columns per page

                # Append the last page's column count
                max1.append(max_cols_per_page)

                data = [[str(item) for item in row] for row in ([
                                                                    st.session_state.filtered_df.columns.tolist()] + st.session_state.filtered_df.values.tolist())]

                data = data[1:]

                long_text_cols = []

                for col_idx in range(st.session_state.filtered_df.shape[1]):
                    cell_values = st.session_state.filtered_df.iloc[2:5, col_idx]

                    if any(len(str(value)) > 45 for value in cell_values):
                        long_text_cols.append(col_idx)

                if not long_text_cols:
                    long_text_cols.append(-1)

                for idx, col in enumerate(st.session_state.filtered_df.columns):
                    if idx in p1 or idx in [x + 1 for x in p1] or idx in [x + 2 for x in p1]:
                        col_widths.insert(idx, 70)

                print(col_widths)

                last_index_of_70 = len(col_widths) - 1 - col_widths[::-1].index(70)

                print(last_index_of_70)

                for i in range(last_index_of_70 + 1, len(col_widths)):
                    if  i not in long_text_cols:
                        col_widths[i] = last_col_size

                print(col_widths)
                if not col_widths:
                    print("Column widths are empty.")
                    return None  # Early return if column widths are not determined

                # Ensure we have columns to display
                if max_cols_per_page == 0:
                    print("No columns fit on the page.")
                    return None  # Early return if no columns can be displayed

                # Define row handling logic as before
                # Constants and initial setup
                max_rows_per_page = row_page + 2
                rows = len(data)
                num_row_pages = (rows // max_rows_per_page) + 1
                num_col_pages = len(max1)

                start_row = 0

                # Iterate over row pages
                for row_page in range(num_row_pages):
                    # Determine row range for the current page
                    start_row = 1 if start_row == 0 else end_row - 1
                    end_row = start_row + max_rows_per_page - 1

                    end_col = 0

                    # Iterate over column pages
                    for col_page in range(num_col_pages):
                        # Determine column range for the current page
                        start_col = end_col
                        end_col = end_col + max1[col_page]

                        # Prepare page data and create the table
                        page_data = [row[start_col:end_col] for row in data[start_row + 1:end_row]]

                        # Extract two header rows from data and insert them into page_data
                        page_data.insert(0, data[0][start_col:end_col])  # Insert the first header row
                        page_data.insert(1, data[1][start_col:end_col])  # Insert the second header row

                        # Skip if page_data is empty
                        if not page_data or not page_data[0]:
                            print("Page data is empty.")
                            continue

                        style_header = ParagraphStyle(name="HeaderStyle", fontSize=fontsize + 1, leading=fontsize + 4,
                                                      textColor="white", fontName="Helvetica-Bold",alignment=TA_CENTER)
                        style_body = ParagraphStyle(name="BodyStyle", fontSize=fontsize, leading=fontsize + 3,
                                                    textColor="black")

                        # Wrap table data into Paragraphs with conditional styles
                        wrapped_data = [
                            [
                                Paragraph(str(item), style_header if row_idx < 2 else style_body)
                                for item in row
                            ]
                            for row_idx, row in enumerate(page_data)
                        ]


                        # Create table and apply styles
                        table = Table(wrapped_data, repeatRows=2 ,colWidths=col_widths[start_col:end_col])
                        table_style = TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 1), colors.red),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 1 * mm),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0 * mm),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ])

                        col_idx = 0
                        while col_idx < len(page_data[0]):
                            start_idx = col_idx
                            # Find the continuous range of identical column headers in row 0.
                            while (col_idx + 1 < len(page_data[0]) and page_data[0][col_idx] == page_data[0][col_idx + 1]):
                                col_idx += 1

                            # If there are identical consecutive column headers, apply merging.
                            if start_idx != col_idx:
                                # use SPAN
                                table_style.add('SPAN', (start_idx, 0), (col_idx, 0))
                                # Clear the duplicate column headers, keeping only the first one.
                                for i in range(start_idx + 1, col_idx + 1):
                                    wrapped_data[0][i] = Paragraph("", style_header)

                            col_idx += 1

                        for col_idx in range(len(page_data[1])):
                            if page_data[0][col_idx] in ("Other", "Others"):
                                table_style.add('SPAN', (col_idx, 0), (col_idx, 1))
                                table_style.add('BACKGROUND', (col_idx, 0), (col_idx, 1), colors.black)
                            else:
                                if page_data[1][col_idx] == "":
                                    # If the value in row 1 is empty, merge row 0 and row 1.
                                    table_style.add('SPAN', (col_idx, 0), (col_idx, 1))
                                elif page_data[1][col_idx] in ("Other", "Others"):
                                    table_style.add('BACKGROUND', (col_idx, 1), (col_idx, 1), colors.black)

                        # use style
                        table.setStyle(table_style)

                        story.append(KeepTogether([table]))

                        # Add page break if not the last row or column page
                        if row_page < num_row_pages - 1 or col_page < num_col_pages - 1:
                            story.append(PageBreak())

                no_gap_style = ParagraphStyle(
                    'NoGapStyle',
                    parent=styles['Normal'],
                    fontSize=12,
                    leading=14,
                    spaceBefore=0,
                    spaceAfter=0,
                )

                # Left and right content

                left_content = [
                    Paragraph(f"Confirmed by ({confirm}):", no_gap_style),
                    Spacer(1, 20),
                    Paragraph("Signature: ______________________________", no_gap_style),
                    Spacer(1, 5),
                    Paragraph(f"Date: {signature_data}", no_gap_style),
                    Paragraph("Name:", no_gap_style),
                    Paragraph("Designation:", no_gap_style),
                ]


                note_lines = [line.strip() for line in note1.split('-') if line.strip()]
                grouped_note_lines = list(split_into_chunks(note_lines, 6))


                combined_data = []

                for i, group in enumerate(grouped_note_lines):

                    note_paragraphs = [
                        Paragraph(f"- {line}" if not (i == 0 and j == 0) else line, no_gap_style)
                        for j, line in enumerate(group)
                    ]


                    left_column = Table([[line] for line in left_content],
                                        colWidths=[5 * inch]) if i == 0 else Paragraph("", no_gap_style)

                    row = [
                        left_column, "",
                        Table([[line] for line in note_paragraphs], colWidths=[5.5 * inch]),
                    ]
                    combined_data.append(row)

                combined_table = Table(combined_data, colWidths=[5 * inch, 5.5 * inch])
                combined_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))


                story.append(Spacer(1, 20))
                story.append(combined_table)

                # Build the PDF and save to buffer
                doc.build(story, onFirstPage=lambda canvas, _: add_page_number_with_header(canvas, _, team, logo_path, confidential,title),
                          onLaterPages=lambda canvas, _: add_page_number_with_header(canvas, _, team, logo_path, confidential, title))

                now = datetime.now()
                today_date = now.strftime('%Y-%m-%d_%H-%M-%S')
                milliseconds = now.strftime('%f')[:3]
                pdf_filename1 = f"{pdf_filename}_{today_date}_{milliseconds}.pdf"

                project_dir = os.path.abspath(os.path.dirname(__file__))

                merge_dir = os.path.join(project_dir, "merge")

                system_pdf_path = os.path.join(merge_dir, pdf_filename1)

                os.makedirs(os.path.dirname(system_pdf_path), exist_ok=True)

                buffer.seek(0)
                with open(system_pdf_path, 'wb') as f:
                    f.write(buffer.read())

                # Allow user to download the PDF
                buffer.seek(0)
                st.download_button(
                    label="Download the generated PDF",
                    data=buffer,
                    file_name=pdf_filename,
                    mime='application/pdf'
                )

        else:
            st.write("Please select at least one column to display.")
    else:
        st.write("Please upload files to start merging and filtering data.")


if st.session_state.page == 'home':
    home_page()
