from flask import Flask, render_template, url_for, request, redirect, session, flash
import openFDA as api
import signal

app = Flask(__name__)
app.secret_key = "admin" # look into proper secret key practices if ever deplying this app

@app.route('/', methods=['POST', 'GET'])
@app.route('/home')

@app.route('/home', methods=['POST', 'GET'])     # home root
def home_page():
    if request.method == 'POST':
        try:
            session["drug_input"] = str(request.form['drug_input'])
            session["reaction_input"] = str(request.form['reaction_input']) 
            session["support_input"] = str(request.form['support_input']) 
            return redirect(url_for('results_page'))
        except:
            # re-route to home page if something went wrong
            flash('Something went wrong', 'danger')
            return redirect(url_for('home_page'))

    return render_template('home.html')


def handler(signum, frame):
    raise Exception("Function has run for too long")




@app.route('/results', methods=['POST', 'GET'])     # results root
def results_page():
    try:
        ddi_results = api.filter_data(session["drug_input"], session["reaction_input"], session["support_input"])
        return render_template('results.html', ddi_results = ddi_results)
    except:
            flash('Try a different minimum support', 'danger')
            return redirect(url_for('home_page'))



if __name__ == '__main__':
    app.run(debug=False)