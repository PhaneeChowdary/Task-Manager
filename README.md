# Task Management System

A full-featured web-based task management system built with **Flask** on the backend and **Bootstrap**, **HTML/CSS**, and **Jinja** on the frontend. The platform enables users to create boards, manage tasks, collaborate with team members, and visualize task progress in a simple and intuitive UI.

## 🚀 Features

### Task Management

-   Create, update, and delete tasks within boards
-   Assign tasks to one or more users
-   Add descriptions, due dates, priorities, and completion status
-   Filter tasks by:
    -   Status (All, Active, Completed)
    -   Search term
    -   Due date (specific date or range)
    -   Created date (specific date or range)
    -   Assigned user
    -   Created by
    -   Sort by (Created Date, Due Date, Priority, Title)

### 🗂 Board Management

-   Create private or shared boards
-   Invite members by email
-   Role-based control (only owners can manage members)
-   View task progress and board summary
-   Export boards and task data

### 👥 User Management

-   Register and log in using secure authentication
-   Update user information
-   Delete user account (automtically exports your data and will send a mail before deletion of your account)
-   Profile page with:
    -   Task summary
    -   Filterable list of assigned or created tasks

### 📊 Dashboard

-   Visual stats (total boards, tasks, completed tasks)
-   Activity graph for task creation trends
-   Recent activity log
-   Quick access to recent and shared boards

### 💬 Task Interaction

-   Inline editing
-   View assigned users
-   View task comments
-   Filter within board scope

## 🛠 Tech Stack

| Layer     | Technology                            |
| --------- | ------------------------------------- |
| Backend   | Python, Flask, Firebase Admin SDK     |
| Frontend  | HTML, CSS, Bootstrap, Jinja Templates |
| Database  | Firebase Firestore                    |
| Auth      | Firebase Authentication               |
| Charts    | Chart.js                              |
| Calendar  | Flatpickr                             |
| Icons     | Bootstrap Icons                       |
| Exporting | CSV, JSON (download support)          |

## ⚙️ Setup Instructions

1. **Clone the repository**

    ```bash
    git clone https://github.com/your-username/task-manager.git
    cd task-manager
    ```

2. **Set up a virtual environment**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure Firebase credentials**

    - Add your Firebase Admin SDK JSON in a secure location
    - Set up `.env` or config vars for your Firebase settings

5. **Run the server**
    ```bash
    python app.py
    ```

## 📸 Screenshots

Here’s a quick visual overview of the application:

-   Home and Login

    ![Dashboard View](/static/Screenshot1.png)

-   Dashboard with stats and activity graph

    ![Dashboard View](/static/Screenshot2.png)

-   Boards and Shared Boards listing

    ![Dashboard View](/static/Screenshot4.png)

-   Board details with filterable task lists

    ![Dashboard View](/static/Screenshot.png)

-   Modals for editing tasks and managing users

    ![Dashboard View](/static/Screenshot5.png)

-   Profile page with personal task filters

    ![Dashboard View](/static/Screenshot0.png)

## Thank you
