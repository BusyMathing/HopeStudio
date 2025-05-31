from functools import wraps
from os import abort

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_pymongo import PyMongo  # 新增MongoDB支持
import datetime

app = Flask(__name__)
# 配置MongoDB
app.config["MONGO_URI"] = "mongodb://localhost:27017/hopestudio"  # 根据实际情况修改数据库名
app.config["SECRET_KEY"] = "6dAUwyVFVQbShAbc4xn7RhnKvGJ3SbtXACRQ3ERGmThrcsJzNBJbvGB6ZAZxHGhmvdVfF8ZEuN7CbENMwDx4s2Sk4ZsRsn8zn8xFMT8SnXHFypSNVwXMBsS2hJQdfnGk8AQGVXMKWYwXZTPwMMvvwdhPf4kEJVdy7NwbjGJRjbXFHW6PRvCTjYuuQQMybRjrbEtKhb2eZTmrANpbsKREZjYSmWsFUjDFmEcWEtFGF22CvxmjufkJB2AVKjte7xnhtbwdyJNt8ZwjApv357MkhDhsWEmxUWtk8AdxaNFNWeHN44CaUpSShDUhMUQfH48DuxaU4ppfmErfRBTKpFN3wjWDbKAksZAuUnFHQtmv5dKrzVBCpU6p6F6x3uU6SMEnsm8p2b6v4xpsP3jHTnRv33p5J3PvhKpSSMZF4s6HrWEAvvnCWd3a3jfbSQzQucpVpF5XS4TQN2B7AVkatfJ8nGBnUeGpzWhP32Bwff3MvDVteJb3kzTKcDFmx2fxZ2tC"  # 设置安全密钥
mongo = PyMongo(app)  # 初始化MongoDB

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 关于我们页面路由
@app.route('/about')
def about():
    return render_template('about.html')

# 团队成员页面路由
@app.route('/team')
def team():
    return render_template('team.html')

# 作品展示页面路由
@app.route('/works')
def works():
    return render_template('works.html')

# 联系方式页面路由
@app.route('/contact')
def contact():
    return render_template('contact.html')

# 用户认证相关路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = mongo.db.users.find_one({'username': username})

        if existing_user:
            return '用户名已存在！'
        
        # 添加注册时间字段和用户类型字段
        mongo.db.users.insert_one({
            'username': username,
            'password': generate_password_hash(password),
            'register_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_type': 'user'  # 默认用户类型为普通用户
        })
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect(url_for('index'))
        
        return '无效的用户名或密码'
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# 添加登录保护装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/user/<username>')
@login_required
def user(username):
    # 允许管理员查看所有用户信息
    current_user = mongo.db.users.find_one({'username': session['user']})
    if current_user['user_type'] != 'admin' and session['user'] != username:
        abort(403)
    
    user = mongo.db.users.find_one({'username': username})
    all_users = list(mongo.db.users.find({})) if current_user['user_type'] == 'admin' else None
    
    # 添加反馈数据查询
    feedback_list = list(mongo.db.feedback.find({})) if current_user['user_type'] == 'admin' else None
    
    if user:
        return render_template('user.html',
                             username=user['username'],
                             register_date=user.get('register_date', '未知时间'),
                             user_type=user['user_type'],
                             all_users=all_users,
                             feedback_list=feedback_list)
    abort(404)

@app.route('/delete_user/<path:username>', methods=['POST'])  # 修改参数类型为path
@login_required
def delete_user(username):
    current_user = mongo.db.users.find_one({'username': session['user']})
    if current_user['user_type'] != 'admin':
        abort()
    
    # 执行删除操作
    mongo.db.users.delete_one({'username': username})
    return redirect(url_for('user', username=session['user']))

@app.route('/edit_user/<path:username>', methods=['GET', 'POST'])  # 修改参数类型为path
@login_required
def edit_user(username):
    current_user = mongo.db.users.find_one({'username': session['user']})
    if current_user['user_type'] != 'admin':
        abort()

    user = mongo.db.users.find_one({'username': username})
    if not user:
        abort()

    if request.method == 'POST':
        # 更新用户信息
        new_username = request.form.get('username')
        new_type = request.form.get('user_type')
        new_password = request.form.get('new_password')  # 获取新密码
        
        # 构建更新数据
        update_data = {'$set': {
            'username': new_username,
            'user_type': new_type
        }}
        
        # 如果有新密码则更新
        if new_password:
            update_data['$set']['password'] = generate_password_hash(new_password)
        
        # 更新用户数据
        mongo.db.users.update_one({'username': username}, update_data)
        
        return redirect(url_for('user', username=session['user']))

    return render_template('edit_user.html', 
                         original_username=user['username'],
                         user_type=user['user_type'])

# 新增用户路由需要添加允许POST方法
@app.route('/add_user', methods=['GET', 'POST'])  # 新增路由需要补充methods参数
@login_required
def add_user():
    # 检查管理员权限
    current_user = mongo.db.users.find_one({'username': session['user']})
    if current_user['user_type'] != 'admin':
        abort(403)

    if request.method == 'POST':
        # 处理表单提交
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 检查用户是否存在
        if mongo.db.users.find_one({'username': username}):
            return render_template('add_user.html', error='用户名已存在')
        
        # 创建新用户
        mongo.db.users.insert_one({
            'username': username,
            'password': generate_password_hash(password),
            'user_type': 'user',
            'register_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return redirect(url_for('user', username=session['user']))

    # GET请求显示添加用户表单
    return render_template('add_user.html')

# 新增测试MongoDB的路由
@app.route('/test-mongo')
def test_mongo():
    # 插入测试数据
    test_collection = mongo.db.test_collection
    test_collection.insert_one({"name": "test", "value": "MongoDB connection works!"})
    
    # 查询数据
    result = test_collection.find_one({"name": "test"})
    return f'MongoDB测试成功！存储的值是：{result["value"]}' if result else "未找到测试数据"

# 添加404错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404

# 新增500错误处理
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', error=e), 500

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        content = request.form.get('content')
        mongo.db.feedback.insert_one({
            'username': session['user'],
            'content': content,
            'submit_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return  redirect('/')
    return render_template('feedback.html')

@app.route('/delete_feedback/<feedback_id>', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    current_user = mongo.db.users.find_one({'username': session['user']})
    if current_user['user_type'] != 'admin':
        abort(403)
    
    from bson import ObjectId
    mongo.db.feedback.delete_one({'_id': ObjectId(feedback_id)})
    return redirect(url_for('user', username=session['user']))


@app.route('/game')
def game():
    return render_template('game.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
    