from Secrets import secrets
from SqlHelper import *
from flask import *
from flask_login import *

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = secrets.get('SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, user_id, username, name, is_worker, biography, location, skills):
        self.id = user_id
        self.username = username
        self.name = name
        self.is_worker = is_worker
        self.biography = biography
        self.location = location
        self.skills = skills
        self.authenticated = False

    def is_authenticated(self):
        return self._authenticated

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


# TODO: Ideally use a separate route for apply button
@app.route('/', methods=['GET', 'POST'])
@login_required
def hello():
    user_id = current_user.get_id()

    if request.method == 'POST':
        data = request.get_json()
        post_id = data.get('postId')

        if post_id:
            #print(f"User {user_id} applied to post {post_id}")
            query, params = applyToPost(user_id, post_id)
            performQuery(query, params)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Post ID not provided'}), 400

    query, params = getUserInfo(user_id)
    userInfo = performQuery(query, params)[0]

    location = userInfo['location']
    skills = userInfo['skills']

    query, params = searchPosts(user_id, location, skills)
    posts = performQuery(query, params)

    return render_template('view_posts.html', posts=posts, location=location)


@app.route('/inbox')
@login_required
def inbox():
    user_id = current_user.get_id()

    query, params = getMessagesReceived(user_id)
    messages = performQuery(query, params)

    return render_template('view_messages.html', messages=messages)


@app.route('/yourPosts')
@login_required
def yourPosts():
    user_id = current_user.get_id()

    query, params = getPostsByAuthor(user_id)
    posts = performQuery(query, params)

    return render_template('view_your_posts.html', posts=posts)


@app.route('/viewApplied')
@login_required
def appliedPosts():
    user_id = current_user.get_id()

    query, params = searchAppliedPosts(user_id)
    posts = performQuery(query, params)
    #print(performQuery(getUsers()))

    return render_template('view_applied.html', posts=posts, location="New York")


@app.route('/viewApplicants')
@login_required
def applicants():
    user_id = current_user.get_id()

    query, params = getApplicantInformationByAuthor(user_id)
    applicants = performQuery(query, params)
    #print(applicants)

    return render_template('view_applicants.html', applicants=applicants)


@app.route('/approveApplicant', methods=['POST'])
@login_required
def approve_applicant():
    data = request.json
    applicant_id = data.get('userId')
    post_id = data.get('postId')
    author_id = current_user.get_id()

    try:
        #print("approved applicant " + applicant_id + " in post " + post_id)

        # Send approval message for position name to inbox
        query, params = getPostTitle(post_id)
        post_title = performQuery(query, params)
        post_title_str = post_title[0]['title'] if post_title else "ERRORED POSITION"

        query, params = sendMessage(author_id, applicant_id,
                                    "Congratulations, You have been approved for position: " + post_title_str)
        performQuery(query, params)

        # Delete applicant from post
        query, params = removeUserApplication(post_id, applicant_id)
        performQuery(query, params)

        # Mark post as closed
        query, params = markPostAsClosed(post_id)
        performQuery(query, params)

        return jsonify({"success": True})
    except Exception as e:
        #print(f"Error approving applicant: {e}")
        return jsonify({"success": False})


@app.route('/denyApplicant', methods=['POST'])
@login_required
def deny_applicant():
    data = request.json
    applicant_id = data.get('userId')
    post_id = data.get('postId')
    author_id = current_user.get_id()

    try:
        #print("denied applicant " + applicant_id + " from post " + post_id)

        # Send denial message from position name to inbox
        query, params = getPostTitle(post_id)
        post_title = performQuery(query, params)
        post_title_str = post_title[0]['title'] if post_title else "ERRORED POSITION"

        query, params = sendMessage(author_id, applicant_id,
                                    "Unfortunately, you have been denied for position: " + post_title_str)
        performQuery(query, params)

        # Delete applicant from post
        query, params = removeUserApplication(post_id, applicant_id)
        performQuery(query, params)

        return jsonify({"success": True})
    except Exception as e:
        #print(f"Error denying applicant: {e}")
        return jsonify({"success": False})


@login_manager.user_loader
def load_user(user_id):
    query, params = getUserInfo(user_id)
    result = performQuery(query, params)

    if result:
        user_data = result[0]
        user = User(
            user_id=user_data['userId'],
            username=user_data['username'],
            name=user_data['name'],
            is_worker=user_data['isWorker'],
            biography=user_data['biography'],
            location=user_data['location'],
            skills=user_data['skills']
        )
        return user
    return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        is_worker = request.form.get('isWorker', 0)
        biography = request.form['biography']
        location = request.form['location']
        skills = request.form['skills']

        # TODO: Validate input
        if username and password and name:
            query, params = createUser(username, password, name, is_worker, biography, location, skills, None)
            performQuery(query, params)

            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        else:
            flash('All required fields must be filled out.', 'error')

    return render_template('register.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # TODO: Ideally hash all passwords, and compare with hashed text here
        if username and password:
            query, params = getUserByUsernamePassword(username, password)
            users = performQuery(query, params)
            if users:
                user_data = users[0]
                user = User(
                    user_id=user_data['userId'],
                    username=user_data['username'],
                    name=user_data['name'],
                    is_worker=user_data['isWorker'],
                    biography=user_data['biography'],
                    location=user_data['location'],
                    skills=user_data['skills']
                )

                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('hello'))
            else:
                flash('Invalid username or password.', 'error')
        else:
            flash('All required fields must be filled out.', 'error')

    return render_template('login.html')


@app.route('/createPosting', methods=['GET', 'POST'])
@login_required
def create_posting():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        min_salary = request.form['min_salary']
        max_salary = request.form['max_salary']
        related_skills = request.form['related_skills']

        # TODO: Validate input, shrink big texts to fit the queries
        if title and description and location and min_salary.isdigit() and max_salary.isdigit():
            query, params = createPost(title, current_user.get_id(), description, location, min_salary, max_salary,
                                       related_skills, 1, None)
            performQuery(query, params)

            flash('Job posting created successfully!', 'success')
            return redirect(url_for('hello'))
        else:
            flash('All fields must be filled out correctly!', 'error')

    return render_template('create_posting.html')


@app.route('/editUser', methods=['GET', 'POST'])
@login_required
def editUser():
    query, params = getUserInfo(current_user.get_id())
    result = performQuery(query, params)

    if result:
        user = result[0]
    else:
        flash("User not found!", "error")
        return redirect(url_for("hello"))

    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        biography = request.form['biography']
        location = request.form['location']
        skills = request.form['skills']
        isWorker = 'isWorker' in request.form

        # TODO: Validate input
        if username and name and biography and location and skills:
            query, params = editCurrentUser(current_user.get_id(), username, name, isWorker, biography, location,
                                            skills)
            performQuery(query, params)

            flash('User info updated successfully!', 'success')
            return redirect(url_for("hello"))
        else:
            flash('All fields must be filled out correctly!', 'error')

    return render_template("edit_user.html", user=user)


@app.route('/editPosting/<int:post_id>', methods=['GET', 'POST'])
@login_required
def editPosting(post_id):
    query, params = getNthPostByAuthor(post_id, current_user.get_id())

    nth_post = performQuery(query, params)[0]

    if not nth_post:
        return redirect(url_for('yourPosts'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        min_salary = request.form['min_salary']
        max_salary = request.form['max_salary']
        related_skills = request.form['related_skills']
        is_open = 'isOpen' in request.form

        # TODO: Validate input
        if title and description and location and min_salary and max_salary and related_skills:
            query, params = editPost(nth_post['postId'], title, description, location, min_salary, max_salary,
                                     related_skills, is_open)
            performQuery(query, params)

            flash('Job posting updated successfully!', 'success')
            return redirect(url_for("yourPosts"))
        else:
            flash('All fields must be filled out correctly!', 'error')

    return render_template('edit_posting.html', post=nth_post, current_number=post_id)


if __name__ == "__main__":
    app.run()
