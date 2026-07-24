const equal = document.getElementById("equal");
const length = document.getElementById("length");
const updown = document.getElementById("updown");
const numbers = document.getElementById("numbers");
const special = document.getElementById("special");
const password = document.getElementById("password");
const password2 = document.getElementById("password2");
const equalCheck = document.getElementById("equal-x");
const lengthCheck = document.getElementById("length-x");
const updownCheck = document.getElementById("updown-x");
const numbersCheck = document.getElementById("numbers-x");
const specialCheck = document.getElementById("special-x");

 let corect1 = false;
 let corect2 = false;
 let corect3 = false;
 let corect4 = false;
 let corect5 = false;

password.addEventListener("input", (e) => {
    const pwd = e.target.value;
    const pwd2 = password2.value;

     corect1 = false;
     corect2 = false;
     corect3 = false;
     corect4 = false;
     corect5 = false;

    if (pwd.length >= 8) {
        lengthCheck.className = "check fa-solid fa-check ";
        length.className = "valid";
        corect1 = true;
        button()

    } else {
        lengthCheck.className = "check fa-solid fa-xmark ";
        length.className = "invalid";
        corect1 = false;
        button()
    }

    if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) {
        updownCheck.className = "check fa-solid fa-check ";
        updown.className = "valid";
        corect2 = true;
        button()
    } else {
        updownCheck.className = "check fa-solid fa-xmark ";
        updown.className = "invalid";
        corect2 = false;
        button()
    }

    if (/\d/.test(pwd)) {
        numbersCheck.className = "check fa-solid fa-check ";
        numbers.className = "valid";
        corect3 = true;
        button()
    } else {
        numbersCheck.className = "check fa-solid fa-xmark ";
        numbers.className = "invalid";
        corect3 = false;
        button()
    }

    if (/[^A-Za-z0-9]/.test(pwd)) {
        specialCheck.className = "check fa-solid fa-check ";
        special.className = "valid";
        corect4 = true;
        button()
    } else {
        specialCheck.className = "check fa-solid fa-xmark ";
        special.className = "invalid";
        corect4 = false;
        button()
    }

    if (pwd === pwd2) {
        equalCheck.className = "check fa-solid fa-check ";
        equal.className = "valid";
        corect5 = true;
        button()
    } else {
        equalCheck.className = "check fa-solid fa-xmark ";
        equal.className = "invalid";
        corect5 = false;
        button()
    }
});
password2.addEventListener("input", (e) => {
    const pwd2 = e.target.value;
    const pwd = password.value;

     corect1 = false;
     corect2 = false;
     corect3 = false;
     corect4 = false;
     corect5 = false;

    if (pwd.length >= 8) {
        lengthCheck.className = "check fa-solid fa-check ";
        length.className = "valid";
        corect1 = true;
        button()

    } else {
        lengthCheck.className = "check fa-solid fa-xmark ";
        length.className = "invalid";
        corect1 = false;
        button()
    }

    if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) {
        updownCheck.className = "check fa-solid fa-check ";
        updown.className = "valid";
        corect2 = true;
        button()
    } else {
        updownCheck.className = "check fa-solid fa-xmark ";
        updown.className = "invalid";
        corect2 = false;
        button()
    }

    if (/\d/.test(pwd)) {
        numbersCheck.className = "check fa-solid fa-check ";
        numbers.className = "valid";
        corect3 = true;
        button()
    } else {
        numbersCheck.className = "check fa-solid fa-xmark ";
        numbers.className = "invalid";
        corect3 = false;
        button()
    }

    if (/[^A-Za-z0-9]/.test(pwd)) {
        specialCheck.className = "check fa-solid fa-check ";
        special.className = "valid";
        corect4 = true;
        button()
    } else {
        specialCheck.className = "check fa-solid fa-xmark ";
        special.className = "invalid";
        corect4 = false;
        button()
    }

    if (pwd === pwd2) {
        equalCheck.className = "check fa-solid fa-check ";
        equal.className = "valid";
        corect5 = true;
        button()
    } else {
        equalCheck.className = "check fa-solid fa-xmark ";
        equal.className = "invalid";
        corect5 = false;
        button()
    }
});

function button() {
    if (corect1 && corect2 && corect3 && corect4 && corect5) {
        document.getElementById("submit").disabled = false;
        document.getElementById("submit").className = "submit-btn enabled";
    }
    else {
        document.getElementById("submit").disabled = true;
        document.getElementById("submit").className = "submit-btn disabled";
    }

}
