from flask import Flask, flash, redirect, jsonify, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
import time
import game
from helpers import apology, jinja_debug
from urllib.parse import unquote
import datetime

# Configure application
app = Flask(__name__)
gamer = game.Game()

# Ensure responses aren't cached
# if app.config["DEBUG"]:
#     @app.after_request
#     def after_request(response):
#         response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#         response.headers["Expires"] = 0
#         response.headers["Pragma"] = "no-cache"
#         return response

# Configure session to use filesystem (instead of signed cookies)
# app.config["SESSION_FILE_DIR"] = mkdtemp()
# #app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# app.permanent_session_lifetime = datetime.timedelta(hours=8)
app.config['SECRET_KEY'] = "Your_secret_string"
# Session(app)
app.jinja_env.filters["debug"] = jinja_debug


@app.route("/", methods=["GET", "POST"])
def index():
    """User welcome screen"""
    if 'id' in session:
        if gamer.in_progress:
            return redirect('/play')
        else:
            return redirect('/wait')
    if 'name' in session:
        return redirect('/wait')

    if request.method == "GET":
        return render_template('index.html')

    # verify name
    name = request.form.get('name')
    if not name:
        return apology('Please provide player name')
    if name in [player.name for player in gamer.players.values()]:
        return apology('Player name already in use')

    session['name'] = name

    # send to waiting room
    return redirect('/wait')


@app.route("/wait",methods=["GET","POST"])
def wait():
    if 'name' not in session:
        return redirect('/')
    if request.method == "POST":
        # add player
        if 'id' not in session or session['id'] not in gamer.players:
            session['id'] = gamer.add_player(session['name'])

    # remove player if necessary
    if 'id' in session and session['id'] not in gamer.players:
        del session['id']

    # if player is in game and game has started, redirect to game
    elif 'id' in session and gamer.in_progress:
        return redirect('/play')

    session['known_status'] = 'playing_cards'
    # update known player count
    session['num_players'] = len(gamer.players)
    return render_template('wait.html',players=[name[0] for name in gamer.scores()])


@app.route("/play")
def play():
    if 'id' not in session:
        return redirect('/wait')
    if session['known_status'] == 'winner':
        del session['id']
        session['known_status'] = 'over'
        return render_template('game_over.html',scores=gamer.final_scores, previous=gamer.previous_turn())
    if session['id'] not in gamer.players:
        return redirect('/wait')
    if not gamer.in_progress:
        success = gamer.new_game()
        if not success[0]:
            return apology(success[1])
    session['card_played'] = (len(gamer.cards_played),len(gamer.guesses))
    print(gamer.previous_turn())
    return render_template('gamer.html',cards=gamer.get_cards(session['id']),scores=gamer.scores(),
                                        giving=session['id'] == gamer.code_giver.id, guessing=gamer.in_play() is not None,
                                        previous=gamer.previous_turn(), giver=gamer.code_giver.name)


@app.route('/waiting', methods=["GET"])
def waiting():
    if gamer.in_progress and 'id' in session:
        return jsonify(True)
    if 'num_players' in session:
        return jsonify(session['num_players'] != len(gamer.players))
    else:
        return jsonify(False)


@app.route("/action", methods=["GET"])
def guess_card():
    card = request.args.get("card")
    if not card or not 'id' in session:
        return jsonify(False)
    else:
        success = gamer.action(session['id'],card)
        return jsonify(success)

@app.route("/get-update", methods=["GET"])
def get_update():
    if not 'known_status' in session:
        return jsonify(True)

    # gamer over?
    if not session['known_status'] == 'winner':
        if not gamer.in_progress:
            session['known_status'] = 'winner'
            return jsonify(True)

    if session['num_players'] != len(gamer.players):
        session['num_players'] = len(gamer.players)
        return jsonify((True))

    # ready to guess?
    if not session['known_status'] == 'in-play':
        in_play = gamer.in_play()
        if in_play:
            session['known_status'] = 'in-play'
            return jsonify(True)

    # done guessing, next round time
    if session['known_status'] == 'in-play':
        in_play = gamer.in_play()
        if not in_play:
            session['known_status'] = 'playing-cards'
            return jsonify(True)

    # someone's played a card
    if session['card_played'] != (len(gamer.cards_played),len(gamer.guesses)):
        session['card_played'] = (len(gamer.cards_played),len(gamer.guesses))
        return jsonify(True)

    return jsonify(False)

@app.route("/remove")
def remove():
    player = request.args.get('player')
    if player:
        return jsonify(gamer.remove_player(player))
    elif 'id' in session:
        del session['id']
        session['known_status'] = 'over'
        return jsonify(gamer.remove_player(session['name']))
    else:
        return jsonify(False)

@app.route("/debug",methods=['GET','POST'])
def debug():
    if request.method == 'POST':
        if 'davey' not in session:
            if request.form.get("password") == 'plaintextpasswordsareprobablydumb':
                session['davey'] = True
            else:
                return jsonify('Go away, Noah.')
        exec(request.form.get("exec"))
    return render_template('debug.html')

