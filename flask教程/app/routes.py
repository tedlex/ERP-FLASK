
from app import app
from app.forms import LoginForm
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_user
from app.models import User, Game, Decision1, Decision2, Result1
from flask_login import logout_user
from flask_login import login_required
from flask import request
from werkzeug.urls import url_parse
from app import db
from app.forms import RegistrationForm
from datetime import datetime
from app.forms import EditProfileForm, Decisions1Form, Decisions2Form, GameForm
import subprocess
import os


@app.route('/')
@app.route('/index')
#@login_required
def index():
    user = {'username': 'Miguel'}
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]
    return render_template('index.html', title='Home', posts=posts)




@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)#登录成功，该函数会
        # 将用户登录状态注册为已登录，这意味着用户
        # 导航到任何未来的页面时，应用都会将用户实例赋值给current_user变量。
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)



@app.route('/user/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    games = Game.query.filter_by(player=current_user).all()
    form = GameForm()

    return render_template('user.html', user=user, games=games, form=form)



@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()



@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/stage1/<gameid>', methods=['GET', 'POST'])
@login_required
def decisions_1(gameid):
    d = Decision1.query.filter_by(gameid=gameid).first() #知道gameid，并且默认知道stage为1，所以可以定位
    #gid = Game.query.filter_by(id=gameid).first_or_404().gid
    g = d.game
    g.last_time=datetime.utcnow()
    db.session.commit()
    form = Decisions1Form()
    if form.validate_on_submit():
        # 提交保存的时候，清除该文件，因为这会在后面仿真的时候判断sim是否完成
        my_file = 'result2.csv'
        if os.path.exists(my_file):
            os.remove(my_file)
        else:
            pass
        d.quality = form.quality.data
        d.batch = form.batch.data
        d.stock = form.stock.data
        d.contract = form.contract.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('decisions_1',gameid=gameid))
    elif request.method == 'GET':
        form.quality.data = d.quality
        form.batch.data = d.batch
        form.stock.data = d.stock
        form.contract.data = d.contract
    return render_template('stage1.html', title='第一阶段',
                           form=form, g=g) #注意这里传进网页的是game对象

@app.route('/stage1/help/<gameid>', methods=['GET', 'POST'])
@login_required
def help_satge1(gameid):
    d = Decision1.query.filter_by(gameid=gameid).first() #知道gameid，并且默认知道stage为1，所以可以定位
    #gid = Game.query.filter_by(id=gameid).first_or_404().gid
    g = d.game
    return render_template('help_stage1.html', title='第一阶段',
                        g=g) #注意这里传进网页的是game对象


@app.route('/stage1/help/pop')
@login_required
def help_satge1_pop():
    return render_template('help_stage1_pop.html', title='第一阶段')



@app.route('/newgame/', methods=['GET', 'POST'])
@login_required
def newgame():
    maxg = Game.query.join(User, Game.user_id == User.id).filter(User.username == current_user.username).order_by(
        Game.gid.desc()).first()
    if maxg:
        maxid=maxg.gid #该用户当前的游戏最大场次
    else:
        maxid=0
    g=Game(gid=maxid+1, stage=1, user_id=current_user.id, start_time=datetime.utcnow(), last_time=datetime.utcnow(),state=1,ps='无') #向数据库中添加新游戏场次
    db.session.add(g)
    db.session.commit()
    gameid = Game.query.filter_by(gid=maxid+1, user_id=current_user.id).first_or_404().id
    d = Decision1(gameid=gameid) #初始化decision1
    db.session.add(d)
    db.session.commit()
    d = Decision2(dc='', location=0, gameid=gameid)
    db.session.add(d)
    db.session.commit()
    return redirect(url_for('decisions_1',gameid=gameid))


@app.route('/stage2/<gameid>', methods=['GET', 'POST'])
@login_required
def decisions_2(gameid):
    d = Decision2.query.filter_by(gameid=gameid).first()

    #gid = Game.query.filter_by(id=gameid).first_or_404().gid
    g = d.game
    form = Decisions2Form()
    if form.validate_on_submit():
        d.dc = form.dc.data
        d.location = form.location.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('decisions_2',gameid=gameid))
    elif request.method == 'GET':
        form.dc.data = d.dc
        form.location.data = d.location
    return render_template('stage2.html', title='第二阶段',
                           form=form, g=g)


@app.route('/stage1/simulation/<gameid>', methods=['GET', 'POST'])
@login_required
def simulation(gameid):
    g=Game.query.filter_by(id=gameid).first()
    g.stage = 2 #更新game的stage，注意这里不用first因为一个d只返回单个game
    r = Result1(gameid=gameid)
    db.session.add(r)
    db.session.commit()
    #print(os.getcwd())

    my_file = 'result2.csv'
    if os.path.exists(my_file):
        with open('app/simulation/export3/test.txt','r') as f:
            result=f.read()
            return result
    else:#如果并没有仿真完成
        args = ['user']
        cmd = 'sh app/simulation/subrun2.sh' + ' ' + str(args[0])
        p = subprocess.Popen(cmd, shell=True)
        return render_template('simulation.html',title='仿真界面', gameid=gameid)

@app.route('/stage1/result/<gameid>', methods=['GET', 'POST'])
@login_required
def result(gameid):
    g=Game.query.filter_by(id=gameid).first()
    r=g.result1.first()
    return render_template('result.html',title='结果界面', r=r, g=g)
