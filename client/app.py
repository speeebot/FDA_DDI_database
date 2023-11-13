from flask import Flask, render_template, url_for, request, redirect, session, flash

app = Flask(__name__)
app.secret_key = "admin" # look into proper secret key practices if ever deplying this app

@app.route('/', methods=['POST', 'GET'])
@app.route('/home', methods=['POST', 'GET'])     # home root
def home_page():
    if request.method == 'POST':
        try:
            session["drug_input"] = str(request.form['drug_input'])
            session["reaction_input"] = str(request.form['reaction_input']) 
            return redirect(url_for('results_page'))
        
        except:
            # re-route to home page if something went wrong
            flash('Something went wrong', 'danger')
            return redirect(url_for('home_page'))

    return render_template('home.html')


@app.route('/results', methods=['POST', 'GET'])     # results root
def results_page():
    # session["drug_input"]
    # session["reaction_input"]
    # ^^ use session variables to create the ddi results with api.py functions

    # mock data
    ddi_results = [['Advil', "Headache", "0.12"], ['Advil', "Headache", "0.12"], ['Advil', "Headache", "0.12"], ['Advil', "Headache", "0.12"],
                 ['Advil', "Headache", "0.12"], ['Advil', "Headache", "0.12"], ['Advil', "Headache", "0.12"], ['Advil', "Headache", "0.12"],
                 ['vancomycin', "Acute Kidney Injury", "1.2"], ['vancomycin', "Acute Kidney Injury", "1.2"], ['vancomycin', "Acute Kidney Injury", "1.2"], ['vancomycin', "Acute Kidney Injury", "1.2"], 
                 ['vancomycin', "Acute Kidney Injury", "1.2"], ['vancomycin', "Acute Kidney Injury", "1.2"], ['vancomycin', "Acute Kidney Injury", "1.2"], ['vancomycin', "Acute Kidney Injury", "1.2"]]    
    return render_template('results.html', ddi_results = ddi_results)


if __name__ == '__main__':
    app.run(debug=True)