from flask import Flask, render_template, url_for, request, redirect, session, flash

app = Flask(__name__)
app.secret_key = "admin" # look into proper secret key practices if ever deplying this app

@app.route('/', methods=['POST', 'GET'])
@app.route('/home', methods=['POST', 'GET'])     # home root
def home_page():
    if request.method == 'POST':
        try:
            # process the info here, fetch fda api ...
            session["input_1"] = str(request.form['input_1'])
            session["input_2"] = str(request.form['input_2'])            
            return redirect(url_for('results_page'))
        except:
            # re-route to home page if something went wrong, display error message
            flash('Some error message!', 'danger')
            return redirect(url_for('home_page'))

    return render_template('home.html')


@app.route('/results', methods=['POST', 'GET'])     # results root
def results_page():
    return render_template('results.html')


if __name__ == '__main__':
    app.run(debug=True)