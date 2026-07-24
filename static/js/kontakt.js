btn = document.getElementById("switch");
id_btn = document.getElementById("id_btn");
username_btn = document.getElementById("username_btn");

btn.addEventListener("click",function(){
    if (btn.checked == true) {
        id_btn.style.color = "gray";
        username_btn.style.color = "lightblue";
    }
    else {
        id_btn.style.color = "lightblue";
        username_btn.style.color = "gray";
    }
});

form = document.getElementById("form");
form.addEventListener("submit",(e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    if (btn.checked == true) {
        window.location.href = "/chat/kontakt/2/" + formData.get("username");
    }
    else {
        window.location.href = "/chat/kontakt/1/" + formData.get("username");
    }
});