import mysql.connector
from Secrets import secrets
from mysql.connector import Error


def performQuery(query):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    obtainedData = None

    try:
        cursor.execute(query)

        if query.strip().lower().startswith('select'):
            obtainedData = cursor.fetchall()
        else:
            conn.commit()

    except Exception as e:
        print(f"MySql error: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return obtainedData


def performQuery(query, params=None):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    obtainedData = None

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().lower().startswith('select'):
            obtainedData = cursor.fetchall()
        else:
            conn.commit()

    except Exception as e:
        print(f"MySQL error: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return obtainedData


def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=secrets.get('DATABASE_PASSWORD'),
            database='data'
        )
        #print("Connection to MySQL DB successful")
    except Error as e:
        print(f"Error Connecting to MySQL: '{e}'")
    return connection


def getUsers():
    return "SELECT * FROM user"


def getPosts():
    return "SELECT * FROM post"


def getMessages():
    return "SELECT * FROM messages"


def createUser(username, password, name, is_worker, biography, location, skills, jobs_applied_ids):
    query = """
    INSERT INTO user (username, password, name, isWorker, biography, location, skills, jobsAppliedIds)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    params = (username, password, name, is_worker, biography, location, skills, jobs_applied_ids)
    return query, params


def createPost(title, authorId, description, location, min_salary, max_salary, skills, is_open, user_ids_applied):
    query = """
    INSERT INTO post (title, authorId, description, location, min_salary, max_salary, skills, isOpen, userIdsApplied)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    params = (title, authorId, description, location, min_salary, max_salary, skills, is_open, user_ids_applied)
    return query, params


def sendMessage(senderId, recipientId, information):
    query = """
    INSERT INTO messages (senderId, recipientId, information)
    VALUES (%s, %s, %s);
    """
    params = (senderId, recipientId, information)
    return query, params


def applyToPost(user_id, post_id):
    query = """
    INSERT INTO user_application (userId, postId)
    VALUES (%s, %s);
    """
    params = (user_id, post_id)

    return query, params


def deleteUser(user_id):
    query = f"""
    DELETE FROM user
    WHERE userId = {user_id};
    """
    return query


def deletePost(post_id):
    query = f"""
    DELETE FROM post
    WHERE postId = {post_id};
    """
    return query


def deleteMessage(message_id):
    query = f"""
    DELETE FROM messages
    WHERE messageId = {message_id};
    """
    return query


def editCurrentUser(user_id, username, name, isWorker, biography, location, skills):
    query = """
    UPDATE user
    SET username = %s,
        name = %s,
        isWorker = %s,
        biography = %s,
        location = %s,
        skills = %s
    WHERE userId = %s;
    """
    params = (username, name, isWorker, biography, location, skills, user_id)
    return query, params


def editPost(post_id, title, description, location, min_salary, max_salary, skills, is_open):
    query = f"""
    UPDATE post
    SET title = %s, description = %s, location = %s, min_salary = %s, max_salary = %s,
        skills = %s, isOpen = %s
    WHERE postId = %s;
    """
    params = (title, description, location, min_salary, max_salary, skills, is_open, post_id)
    return query, params


def getUserInfo(userId):
    query = """
    SELECT * FROM user WHERE userId = %s;
    """
    return query, (userId,)


def getUserByUsernamePassword(username, password):
    query = """
    SELECT * FROM user WHERE username = %s AND password = %s LIMIT 1;
    """
    return query, (username, password)


def getNthPostByAuthor(n, x):
    query = """
    SELECT * FROM post
    WHERE authorId = %s
    ORDER BY postId ASC
    LIMIT 1 OFFSET %s
    """
    params = (x, n - 1)
    return query, params


def getPostTitle(post_id):
    query = """
    SELECT title
    FROM post
    WHERE postId = %s;
    """
    params = (post_id,)
    return query, params


# Search 'post' table for posts that:
# given userId has not applied to it
# given location is a match
# the post is open
# sorted by skills in common + recency
def searchPosts(userId, location, skills):

    skill_list = [skill.strip() for skill in skills.split(",")]

    skill_conditions = " + ".join(
        [f"FIND_IN_SET(%s, skills)" for _ in skill_list]
    )

    query = f"""
    SELECT 
        postId, title, description, location, min_salary, max_salary, skills, isOpen, userIdsApplied, authorId,
        ({skill_conditions}) AS skill_matches
    FROM post
    WHERE 
        isOpen = 1
        AND location = %s
        AND authorId != %s
        AND NOT EXISTS (
            SELECT 1 
            FROM user_application 
            WHERE user_application.userId = %s 
              AND user_application.postId = post.postId
        )
    ORDER BY skill_matches DESC, postId DESC;
    """

    params = skill_list + [location, userId, userId]

    return query, params



def searchAppliedPosts(userId):
    query = """
        SELECT p.*
        FROM post p
        JOIN user_application ua ON p.postId = ua.postId
        WHERE ua.userId = %s;

    """
    params = (userId,)
    return query, params


def getMessagesReceived(user_id):
    query = """
    SELECT 
        m.information, 
        m.timestamp, 
        u.name AS sender_name 
    FROM messages m
    JOIN user u ON m.senderId = u.userId
    WHERE m.recipientId = %s
    ORDER BY m.timestamp DESC;
    """
    params = (user_id,)
    return query, params


def getApplicantsByAuthor(user_id):
    query = """
    SELECT 
        DISTINCT ua.userId
    FROM 
        post p
    JOIN 
        user_application ua ON p.postId = ua.postId
    WHERE 
        p.authorId = %s;
    """
    params = (user_id,)
    return query, params


def getApplicantInformationByAuthor(user_id):
    query = """
    SELECT 
        u.name,
        u.skills,
        u.biography,
        p.title,
        ua.postId,
        ua.userId
    FROM user_application ua
    JOIN user u ON ua.userId = u.userId
    JOIN post p ON ua.postId = p.postId
    WHERE p.authorId = %s
    """
    params = (user_id,)
    return query, params


def getPostsByAuthor(author_id):
    query = """
    SELECT *
    FROM post
    WHERE authorId = %s;
    """
    params = (author_id,)
    return query, params


def removeUserApplication(post_id, user_id):
    query = """
    DELETE FROM user_application
    WHERE postId = %s AND userId = %s;
    """
    params = (post_id, user_id)
    return query, params


def deleteApplicationsFromPost(post_id):
    query = """
    DELETE FROM user_application
    WHERE postId = %s;
    """
    params = (post_id,)
    return query, params


def markPostAsClosed(post_id):
    query = """
    UPDATE post
    SET isOpen = 0
    WHERE postId = %s;
    """
    params = (post_id,)
    return query, params
