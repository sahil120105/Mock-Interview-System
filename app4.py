import streamlit as st
from langchain_groq import ChatGroq
import PyPDF2
from docx import Document as DocxDocument
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import time
from fpdf import FPDF
import os
from dotenv import load_dotenv

load_dotenv()

chat = ChatGroq(
    api_key=os.getenv('GROQ_API_KEY'),  # Replace with your API key
    model_name="mixtral-8x7b-32768"
)


# function to parse pdf
def parse_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()
    return text


# function to parse text document
def parse_docx(file):
    doc = DocxDocument(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


# function to fetch questions
@st.cache_data(ttl=600)
def fetch_questions(resume_text, num_qs):
    system = "You are a helpful assistant."
    human = "{text}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human",
             f"""You are an experienced interviewer and have good industry knowledge as well as candidate evaluation skills.Based on the following resume content,
              generate relevant interview questions. Remember, the questions should be challenging and should be such that they extract the candidate's 
              technical as well as soft skills. Be sure to ask about his past experiences too. Ask {num_qs} questions only. Be sure you do a thorough evaluation
              with the limited number of questions you have specified. Make sure that there is a £ sign after each question ends but dont include this 
              sign after the question number {num_qs}. Follow this instruction very strictly, there must be no mistake in it. Only provide the questions
              Don't say anything else:
             \n\n{resume_text}\n\nInterview Questions: """)
        ]
    )

    chain = prompt | chat | StrOutputParser()
    output = chain.invoke({"text": resume_text})
    if output.endswith("£"):
        output = output[:-1]
    output = output.split('£')



    return output


# function to fetch feedback
def fetch_feedback(resume_text, combined_string):
    system = "You are a helpful assistant."
    human = "{text}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human",
             f"""Based on the following resume content and interview question and answers, provide feedback on the candidate's 
             performance highlighting his strengths and areas of weaknessMake sure you do not go easy 
             on the candidate. If he lacks a certain skill or aspect make it clear and do not sugarcoat anything:
             \n\n{resume_text}\n\n{combined_string}\n\nFeedback:""")
        ]
    )

    chain = prompt | chat | StrOutputParser()
    output = chain.invoke({"text": resume_text})

    return output


# function to fetch report
def fetch_report(resume_text, combined_string):
    system = "You are a helpful assistant."
    human = "{text}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human",
             f"""Based on the following resume content and interview question and answers, provide an evaluations on the
              candidate's performance.Summarize the interview an also focus on how he answered the questions. Highlight his 
              strengths and weaknesses. Also suggest on how he can improve himself and his skills. Make sure you do not go easy 
              on the candidate. If he lacks a certain skill or aspect make it clear and do not sugarcoat anything.
              The format must be:

              Introduction to the candidate's performance
              Technical skills
              Problem Solving Ability
              Communication skills
              Teamwork and colaboration
              Strengths 
              Areas of improvements
              Overall impression
              Recommendation

              :\n\n{resume_text}\n\n{combined_string}\n\nEvaluation:""")
        ]
    )

    chain = prompt | chat | StrOutputParser()
    output = chain.invoke({"text": resume_text})

    return output


#make report pdf
def create_pdf(report_text):
    pdf = FPDF()
    pdf.add_page()
    # Add title
    pdf.set_font("Arial", size=16)  # Larger font size for the title
    pdf.cell(200, 10, txt="Evaluation Report", ln=True, align='C')

    # Add paragraph
    pdf.set_font("Arial", size=12)  # Normal font size for the paragraph
    pdf.multi_cell(0, 10, report_text)  # Use multi_cell for paragraph text

    # Save the PDF to a file
    local_directory = "report_pdfs"
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)
    pdf_file_path = os.path.join(local_directory, "Evaluation.pdf")
    pdf.output(pdf_file_path)

    return pdf_file_path

# Function to download PDF
def download_pdf(file_path):
    with open(file_path, "rb") as file:
        btn = st.download_button(
            label="Download Report PDF",
            data=file,
            file_name="Evaluation.pdf",
            mime="application/pdf"
        )
        return btn


def main():
    st.title("Mock Interview")

    # upload resume
    uploaded_file = st.file_uploader("Upload your resume (PDF/DOCX)", type=["pdf", "docx"])

    # logic to parse file
    if uploaded_file is not None:
        st.success("Resume uploaded successfully")

        if uploaded_file.type == "application/pdf":
            resume_text = parse_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            resume_text = parse_docx(uploaded_file)

        # st.text_area("Extracted Resume Text", resume_text, height=300)

        num_qs = st.slider("Enter the number of questions you want :", min_value=1, max_value=10)
        time.sleep(3)

        # generate questions from the resume text
        questions = fetch_questions(resume_text, num_qs)
        #st.write(questions)

        responses = []
        for i in range(len(questions)):
            st.write(questions[i])
            ans = st.text_area("Answer", height=300, key=f"response_{i}")
            responses.append(ans)

        interview_text = ""
        if st.button("Get Feedback"):
            combined_list = [(q, r) for q, r in zip(questions, responses)]
            combined_string = " ".join([f"{q} \n\n Answer: {r}\n\n " for q, r in combined_list])
            interview_text = combined_string

            feedback = fetch_feedback(resume_text, interview_text)
            st.write(f"Feedback:\n\n {feedback}")


        if st.button("Generate PDF Report"):
            evaluation = fetch_report(resume_text, interview_text)
            pdf_file_path = create_pdf(evaluation)
            st.success("PDF generated successfully!")
            download_pdf(pdf_file_path)


if __name__ == "__main__":
    main()