


/* Калькулятор ТЭР */
/* Редирект кнопки */

function redirect() {
    let second = document.querySelector(".second");
    second.addEventListener("click", () => {
        window.location.href = "/calczerna.html";
    })
}

/* Редирект кнопки */
function getSort(id) {
    let sortPsh = document.getElementById(`choise-${id}`).value;
    console.log(sortPsh);
    let fivth = document.querySelector(`.fivth-${id}`).innerHTML = sortPsh;

}

function percent(id) {

    let fouth = document.querySelector(`.fouth-${id}`).value;
    let firstPerc = document.getElementById(`beforesush-${id}`).value;
    let secondPerc = document.getElementById(`aftersush-${id}`).value;
    let a = firstPerc && secondPerc;
    if (firstPerc == 0.135 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.57;
    } else if (firstPerc == 0.140 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.145 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.75;
    } else if (firstPerc == 0.15 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.155 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.89;
    } else if (firstPerc == 0.16 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.165 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.01;
    } else if (firstPerc == 0.17 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.175 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.13;
    } else if (firstPerc == 0.18 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.185 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.23;
    } else if (firstPerc == 0.19 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.195 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.32;
    } else if (firstPerc == 0.2 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.205 && secondPerc == 0.12) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;

    } else if (firstPerc == 0.14 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.54;
    } else if (firstPerc == 0.145 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.64;
    } else if (firstPerc == 0.15 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.155 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.78;
    } else if (firstPerc == 0.16 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.165 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.17 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.175 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.18 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.185 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.19 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.20;
    } else if (firstPerc == 0.195 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.2 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.27;
    } else if (firstPerc == 0.205 && secondPerc == 0.125) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.33;
    } else if (firstPerc == 0.145 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.51;
    } else if (firstPerc == 0.15 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.6;
    } else if (firstPerc == 0.155 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.66;
    } else if (firstPerc == 0.16 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.165 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.170 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.87;
    } else if (firstPerc == 0.175 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.18 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1;
    } else if (firstPerc == 0.185 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.05;
    } else if (firstPerc == 0.19 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.195 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.2 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.205 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.21 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.215 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.22 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.15 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.47;
    } else if (firstPerc == 0.155 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.57;
    } else if (firstPerc == 0.16 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.165 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.17 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.76;
    } else if (firstPerc == 0.175 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.18 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.88;
    } else if (firstPerc == 0.185 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.19 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1;
    } else if (firstPerc == 0.195 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.05;
    } else if (firstPerc == 0.2 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.205 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.21 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.215 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.22 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.27;
    } else if (firstPerc == 0.16 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.54;
    } else if (firstPerc == 0.165 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.6;
    } else if (firstPerc == 0.17 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.67;
    } else if (firstPerc == 0.175 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.73;
    } else if (firstPerc == 0.18 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.185 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.19 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.195 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.2 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1;
    } else if (firstPerc == 0.205 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.21 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.215 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.22 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.16 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.54;
    } else if (firstPerc == 0.165 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.6;
    } else if (firstPerc == 0.17 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.67;
    } else if (firstPerc == 0.175 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.73;
    } else if (firstPerc == 0.18 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.185 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.19 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.195 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.2 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1;
    } else if (firstPerc == 0.205 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.21 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.215 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.22 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.20;
    } else if (firstPerc == 0.16 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.42;
    } else if (firstPerc == 0.165 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.52;
    } else if (firstPerc == 0.17 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.57;
    } else if (firstPerc == 0.175 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.64;
    } else if (firstPerc == 0.18 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.185 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.78;
    } else if (firstPerc == 0.19 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.195 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.89;
    } else if (firstPerc == 0.2 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.205 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.99;
    } else if (firstPerc == 0.21 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.215 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.22 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.13;
    } else if (firstPerc == 0.17 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.49;
    } else if (firstPerc == 0.175 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.55;
    } else if (firstPerc == 0.18 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.185 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.19 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.195 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.2 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.87;
    } else if (firstPerc == 0.205 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.21 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.215 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.01;
    } else if (firstPerc == 0.22 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.17 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.38;
    } else if (firstPerc == 0.175 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.47;
    } else if (firstPerc == 0.18 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.53;
    } else if (firstPerc == 0.185 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.59;
    } else if (firstPerc == 0.19 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.66;
    } else if (firstPerc == 0.195 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.73;
    } else if (firstPerc == 0.2 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.79;
    } else if (firstPerc == 0.205 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.21 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.215 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.22 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.01;
    } else if (firstPerc == 0.18 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.46;
    } else if (firstPerc == 0.185 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.5;
    } else if (firstPerc == 0.19 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.57;
    } else if (firstPerc == 0.195 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.64;
    } else if (firstPerc == 0.2 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.72;
    } else if (firstPerc == 0.205 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.78;
    } else if (firstPerc == 0.21 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.215 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.22 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.18 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.35;
    } else if (firstPerc == 0.185 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.44;
    } else if (firstPerc == 0.19 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.49;
    } else if (firstPerc == 0.195 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.56;
    } else if (firstPerc == 0.2 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.205 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.21 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.77;
    } else if (firstPerc == 0.215 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.22 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.89;
    } else if (firstPerc == 0.19 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.42;
    } else if (firstPerc == 0.195 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.46;
    } else if (firstPerc == 0.2 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.54;
    } else if (firstPerc == 0.205 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.61;
    } else if (firstPerc == 0.21 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.69;
    } else if (firstPerc == 0.215 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.76;
    } else if (firstPerc == 0.22 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.195 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.42;
    } else if (firstPerc == 0.2 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.47;
    } else if (firstPerc == 0.205 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.53;
    } else if (firstPerc == 0.21 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.6;
    } else if (firstPerc == 0.215 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.22 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.75;
    } else if (firstPerc == 0.2 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.41;
    } else if (firstPerc == 0.205 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.43;
    } else if (firstPerc == 0.21 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.52;
    } else if (firstPerc == 0.215 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.59;
    } else if (firstPerc == 0.22 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.205 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.39;
    } else if (firstPerc == 0.21 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.46;
    } else if (firstPerc == 0.215 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.52;
    } else if (firstPerc == 0.22 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.58;
    } else if (firstPerc == 0.22 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.51;
    } else if (firstPerc == 0.23 && secondPerc == 0.13) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.225 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.31;
    } else if (firstPerc == 0.23 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.235 && secondPerc == 0.135) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.46;
    } else if (firstPerc == 0.225 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.27;
    } else if (firstPerc == 0.23 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.31;
    } else if (firstPerc == 0.235 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.39;
    } else if (firstPerc == 0.24 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.46;
    } else if (firstPerc == 0.245 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.5;
    } else if (firstPerc == 0.25 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.54;
    } else if (firstPerc == 0.255 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.58;
    } else if (firstPerc == 0.26 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.63;
    } else if (firstPerc == 0.265 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.27 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.275 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.28 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.88;
    } else if (firstPerc == 0.285 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.96;
    } else if (firstPerc == 0.29 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.01;
    } else if (firstPerc == 0.295 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.3 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.14;
    } else if (firstPerc == 0.305 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.225 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.23 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.235 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.24 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.245 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.25 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.47;
    } else if (firstPerc == 0.255 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.52;
    } else if (firstPerc == 0.26 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.57;
    } else if (firstPerc == 0.265 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.27 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.275 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.28 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.82;
    } else if (firstPerc == 0.285 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.88;
    } else if (firstPerc == 0.29 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.295 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.01;
    } else if (firstPerc == 0.3 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.305 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.14;
    } else if (firstPerc == 0.225 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.23 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.235 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.24 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.245 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.25 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.255 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.45;
    } else if (firstPerc == 0.26 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.5;
    } else if (firstPerc == 0.265 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.56;
    } else if (firstPerc == 0.27 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.275 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.28 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.285 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.82;
    } else if (firstPerc == 0.29 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.88;
    } else if (firstPerc == 0.295 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.3 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.01;
    } else if (firstPerc == 0.305 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.225 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.07;
    } else if (firstPerc == 0.23 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.235 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.24 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.245 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.27;
    } else if (firstPerc == 0.25 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.255 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.40;
    } else if (firstPerc == 0.26 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.44;
    } else if (firstPerc == 0.265 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.5;
    } else if (firstPerc == 0.27 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.56;
    } else if (firstPerc == 0.275 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.28 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.285 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.29 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.82;
    } else if (firstPerc == 0.295 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.3 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.305 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.01;
    } else if (firstPerc == 0.225 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.0;
    } else if (firstPerc == 0.23 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.05;
    } else if (firstPerc == 0.235 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.24 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.245 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.25 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.28;
    } else if (firstPerc == 0.255 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.26 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.39;
    } else if (firstPerc == 0.265 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.27 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.5;
    } else if (firstPerc == 0.275 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.56;
    } else if (firstPerc == 0.28 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.63;
    } else if (firstPerc == 0.285 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.29 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.295 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.3 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.305 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.225 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.95;
    } else if (firstPerc == 0.23 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.99;
    } else if (firstPerc == 0.235 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.24 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.245 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.13;
    } else if (firstPerc == 0.25 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.20;
    } else if (firstPerc == 0.255 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.26 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.265 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.27 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.45;
    } else if (firstPerc == 0.275 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.5;
    } else if (firstPerc == 0.28 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.56;
    } else if (firstPerc == 0.285 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.29 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.295 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.3 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.305 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.225 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.88;
    } else if (firstPerc == 0.23 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.235 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.24 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.01;
    } else if (firstPerc == 0.245 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.25 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.13;
    } else if (firstPerc == 0.255 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.20;
    } else if (firstPerc == 0.26 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.27;
    } else if (firstPerc == 0.265 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.31;
    } else if (firstPerc == 0.27 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.39;
    } else if (firstPerc == 0.275 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.44;
    } else if (firstPerc == 0.28 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.5;
    } else if (firstPerc == 0.285 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.29 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.295 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.3 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.305 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.225 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.23 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.87;
    } else if (firstPerc == 0.235 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.24 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.245 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.0;
    } else if (firstPerc == 0.25 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.07;
    } else if (firstPerc == 0.255 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.26 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.265 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.27 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.31;
    } else if (firstPerc == 0.275 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.28 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.285 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.29 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.57;
    } else if (firstPerc == 0.295 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.3 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.305 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.225 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.23 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.80;
    } else if (firstPerc == 0.235 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.24 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.245 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.25 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1;
    } else if (firstPerc == 0.255 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.07;
    } else if (firstPerc == 0.26 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.13;
    } else if (firstPerc == 0.265 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.27 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.275 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.28 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.285 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.29 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.295 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.54;
    } else if (firstPerc == 0.3 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.305 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.225 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.67;
    } else if (firstPerc == 0.23 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.235 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.24 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.245 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.89;
    } else if (firstPerc == 0.25 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.95;
    } else if (firstPerc == 0.255 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.99;
    } else if (firstPerc == 0.26 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.05;
    } else if (firstPerc == 0.265 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.27 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.275 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.28 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.285 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.29 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.295 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.3 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.54;
    } else if (firstPerc == 0.305 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.225 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.58;
    } else if (firstPerc == 0.23 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.66;
    } else if (firstPerc == 0.235 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.73;
    } else if (firstPerc == 0.24 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.245 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.25 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.89;
    } else if (firstPerc == 0.255 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.26 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.99;
    } else if (firstPerc == 0.265 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.05;
    } else if (firstPerc == 0.27 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.275 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.28 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.285 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.29 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.295 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.3 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.305 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.54;
    } else if (firstPerc == 0.23 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.57;
    } else if (firstPerc == 0.235 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.66;
    } else if (firstPerc == 0.24 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.72;
    } else if (firstPerc == 0.245 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.79;
    } else if (firstPerc == 0.25 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.255 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.88;
    } else if (firstPerc == 0.26 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.265 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.27 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.05;
    } else if (firstPerc == 0.275 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.28 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.285 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.29 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.295 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.3 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.305 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.24 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.65;
    } else if (firstPerc == 0.245 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.71;
    } else if (firstPerc == 0.25 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.78;
    } else if (firstPerc == 0.255 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.26 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.88;
    } else if (firstPerc == 0.265 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.93;
    } else if (firstPerc == 0.27 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.99;
    } else if (firstPerc == 0.275 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.28 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.12;
    } else if (firstPerc == 0.285 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.29 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.24;
    } else if (firstPerc == 0.295 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.3 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.305 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.24 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.56;
    } else if (firstPerc == 0.245 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.64;
    } else if (firstPerc == 0.25 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.255 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.77;
    } else if (firstPerc == 0.26 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.265 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.87;
    } else if (firstPerc == 0.27 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.275 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.28 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.285 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.29 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.295 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.3 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.305 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.24 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.49;
    } else if (firstPerc == 0.245 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.56;
    } else if (firstPerc == 0.25 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.64;
    } else if (firstPerc == 0.255 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.26 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.77;
    } else if (firstPerc == 0.265 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.27 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.87;
    } else if (firstPerc == 0.275 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.28 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.285 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.29 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.295 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.17;
    } else if (firstPerc == 0.3 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.305 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.24 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.42;
    } else if (firstPerc == 0.245 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.48;
    } else if (firstPerc == 0.25 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.54;
    } else if (firstPerc == 0.255 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.63;
    } else if (firstPerc == 0.26 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.7;
    } else if (firstPerc == 0.265 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.76;
    } else if (firstPerc == 0.27 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.275 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.28 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.285 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.29 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.295 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.3 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.305 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.26 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.265 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.69;
    } else if (firstPerc == 0.27 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.76;
    } else if (firstPerc == 0.275 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.28 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.86;
    } else if (firstPerc == 0.285 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.29 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.295 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.3 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.305 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.26 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.54;
    } else if (firstPerc == 0.265 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.27 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.69;
    } else if (firstPerc == 0.275 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.75;
    } else if (firstPerc == 0.28 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.82;
    } else if (firstPerc == 0.285 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.29 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.92;
    } else if (firstPerc == 0.295 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.3 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.305 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.28 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.75;
    } else if (firstPerc == 0.285 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.29 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.295 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.3 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.305 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.28 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.285 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.29 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.295 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.3 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.305 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.28 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.285 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.29 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.295 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.3 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.305 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.29 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.295 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.3 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.305 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.29 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.62;
    } else if (firstPerc == 0.295 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.3 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.305 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.295 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.61;
    } else if (firstPerc == 0.3 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.68;
    } else if (firstPerc == 0.305 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.31 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.315 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.32 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.325 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.33 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.52;
    } else if (firstPerc == 0.335 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.34 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.345 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.7;
    } else if (firstPerc == 0.35 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.355 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.36 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.9;
    } else if (firstPerc == 0.365 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.95;
    } else if (firstPerc == 0.37 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.375 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.08;
    } else if (firstPerc == 0.38 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.14;
    } else if (firstPerc == 0.385 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.2;
    } else if (firstPerc == 0.39 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.28;
    } else if (firstPerc == 0.395 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.33;
    } else if (firstPerc == 0.4 && secondPerc == 0.14) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.4;
    } else if (firstPerc == 0.31 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.20;
    } else if (firstPerc == 0.315 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.25;
    } else if (firstPerc == 0.32 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.33;
    } else if (firstPerc == 0.325 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.33 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.46;
    } else if (firstPerc == 0.335 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.52;
    } else if (firstPerc == 0.34 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.345 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.35 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.71;
    } else if (firstPerc == 0.355 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.36 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.84;
    } else if (firstPerc == 0.365 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.9;
    } else if (firstPerc == 0.37 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.375 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.38 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.08;
    } else if (firstPerc == 0.385 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.14;
    } else if (firstPerc == 0.39 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.21;
    } else if (firstPerc == 0.395 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.28;
    } else if (firstPerc == 0.4 && secondPerc == 0.145) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.34;
    } else if (firstPerc == 0.31 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.315 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.32 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.325 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.33;
    } else if (firstPerc == 0.33 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.4;
    } else if (firstPerc == 0.335 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.46;
    } else if (firstPerc == 0.34 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.52;
    } else if (firstPerc == 0.345 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.57;
    } else if (firstPerc == 0.35 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.355 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.71;
    } else if (firstPerc == 0.36 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.365 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.37 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.89;
    } else if (firstPerc == 0.375 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.38 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.385 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.08;
    } else if (firstPerc == 0.39 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.15;
    } else if (firstPerc == 0.395 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.21;
    } else if (firstPerc == 0.4 && secondPerc == 0.15) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.28;
    } else if (firstPerc == 0.31 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.315 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.32 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.325 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.33 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.33;
    } else if (firstPerc == 0.335 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.34 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.345 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.35 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.355 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.36 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.71;
    } else if (firstPerc == 0.365 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.37 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.375 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.89;
    } else if (firstPerc == 0.38 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.385 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.39 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.09;
    } else if (firstPerc == 0.395 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.15;
    } else if (firstPerc == 0.4 && secondPerc == 0.155) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.21;
    } else if (firstPerc == 0.31 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.315 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.32 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.14;
    } else if (firstPerc == 0.325 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.33 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.27;
    } else if (firstPerc == 0.335 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.33;
    } else if (firstPerc == 0.34 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.345 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.35 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.52;
    } else if (firstPerc == 0.355 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.36 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.365 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.7;
    } else if (firstPerc == 0.37 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.375 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.38 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.89;
    } else if (firstPerc == 0.385 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.39 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.395 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.09;
    } else if (firstPerc == 0.4 && secondPerc == 0.16) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.15;
    } else if (firstPerc == 0.31 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.315 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.0;
    } else if (firstPerc == 0.32 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.325 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.33 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.20;
    } else if (firstPerc == 0.335 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.27;
    } else if (firstPerc == 0.34 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.345 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.38;
    } else if (firstPerc == 0.35 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.355 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.36 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.365 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.37 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.70;
    } else if (firstPerc == 0.375 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.76;
    } else if (firstPerc == 0.38 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.385 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.89;
    } else if (firstPerc == 0.39 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.395 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.4 && secondPerc == 0.165) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.08;
    } else if (firstPerc == 0.31 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.315 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.91;
    } else if (firstPerc == 0.32 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.325 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.33 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.14;
    } else if (firstPerc == 0.335 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.34 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.345 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.35 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.355 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.36 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.365 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.37 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.375 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.7;
    } else if (firstPerc == 0.38 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.385 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.39 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.9;
    } else if (firstPerc == 0.395 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.4 && secondPerc == 0.17) {
        document.querySelector(`.fouth-${id}`).innerHTML = 3.02;
    } else if (firstPerc == 0.31 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.315 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.32 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.325 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.33 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.335 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.14;
    } else if (firstPerc == 0.34 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.345 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.25;
    } else if (firstPerc == 0.35 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.355 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.38;
    } else if (firstPerc == 0.36 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.46;
    } else if (firstPerc == 0.365 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.37 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.57;
    } else if (firstPerc == 0.375 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.38 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.7;
    } else if (firstPerc == 0.385 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.39 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.395 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.9;
    } else if (firstPerc == 0.4 && secondPerc == 0.175) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.96;
    } else if (firstPerc == 0.31 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.315 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.8;
    } else if (firstPerc == 0.32 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.325 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.33 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.01;
    } else if (firstPerc == 0.335 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.34 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.345 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.35 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.355 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.36 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.365 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.37 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.375 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.57;
    } else if (firstPerc == 0.38 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.385 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.7;
    } else if (firstPerc == 0.39 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.395 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.4 && secondPerc == 0.18) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.9;
    } else if (firstPerc == 0.31 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.315 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.32 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.325 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.33 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.335 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.01;
    } else if (firstPerc == 0.34 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.345 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.35 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.355 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.36 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.365 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.37 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.375 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.38 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.57;
    } else if (firstPerc == 0.385 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.39 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.71;
    } else if (firstPerc == 0.395 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.4 && secondPerc == 0.185) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.83;
    } else if (firstPerc == 0.31 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.315 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.32 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.325 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.33 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.88;
    } else if (firstPerc == 0.335 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.34 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.345 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.35 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.355 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.36 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.365 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.37 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.375 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.38 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.385 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.57;
    } else if (firstPerc == 0.39 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.395 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.7;
    } else if (firstPerc == 0.4 && secondPerc == 0.19) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.77;
    } else if (firstPerc == 0.31 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.315 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.32 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.325 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.33 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.82;
    } else if (firstPerc == 0.335 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.88;
    } else if (firstPerc == 0.34 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.345 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.35 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.355 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.36 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.365 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.37 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.375 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.38;
    } else if (firstPerc == 0.38 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.385 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.39 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.395 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.4 && secondPerc == 0.195) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.71;
    } else if (firstPerc == 0.31 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.315 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.32 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.325 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.33 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.335 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.82;
    } else if (firstPerc == 0.34 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.345 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.93;
    } else if (firstPerc == 0.35 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.355 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.36 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.365 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.37 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.375 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.38 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.38;
    } else if (firstPerc == 0.385 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.39 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.52;
    } else if (firstPerc == 0.395 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.4 && secondPerc == 0.2) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.64;
    } else if (firstPerc == 0.31 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.315 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.32 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.325 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.33 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.335 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.34 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.345 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.35 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.355 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.36 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.365 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.37 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.375 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.25;
    } else if (firstPerc == 0.38 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.385 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.38;
    } else if (firstPerc == 0.39 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.395 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.52;
    } else if (firstPerc == 0.4 && secondPerc == 0.205) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.58;
    } else if (firstPerc == 0.31 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.315 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.41;
    } else if (firstPerc == 0.32 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.325 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.33 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.63;
    } else if (firstPerc == 0.335 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.69;
    } else if (firstPerc == 0.34 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.345 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.35 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.355 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.36 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.365 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.37 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.375 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.38 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.25;
    } else if (firstPerc == 0.385 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.39 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.395 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.4 && secondPerc == 0.21) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.51;
    } else if (firstPerc == 0.31 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.315 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.32 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.325 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.33 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.335 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.34 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.345 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.35 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.355 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.36 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.365 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.37 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.375 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.38 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.18;
    } else if (firstPerc == 0.385 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.25;
    } else if (firstPerc == 0.39 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.395 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.4 && secondPerc == 0.215) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.45;
    } else if (firstPerc == 0.31 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.315 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.32 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.325 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.33 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.335 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.34 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.345 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.35 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.355 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.36 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.365 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.93;
    } else if (firstPerc == 0.37 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.375 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.38 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.12;
    } else if (firstPerc == 0.385 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.18;
    } else if (firstPerc == 0.39 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.395 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.4 && secondPerc == 0.22) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.39;
    } else if (firstPerc == 0.31 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.315 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.32 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.325 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.33 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.335 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.34 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.345 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.35 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.355 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.36 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.365 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.37 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.93;
    } else if (firstPerc == 0.375 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.99;
    } else if (firstPerc == 0.38 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.385 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.12;
    } else if (firstPerc == 0.39 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.2;
    } else if (firstPerc == 0.395 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.4 && secondPerc == 0.225) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.32;
    } else if (firstPerc == 0.31 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.315 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.32 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.325 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.33 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.335 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.34 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.345 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.35 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.355 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.67;
    } else if (firstPerc == 0.36 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.365 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.8;
    } else if (firstPerc == 0.37 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.375 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.93;
    } else if (firstPerc == 0.38 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.99;
    } else if (firstPerc == 0.385 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.39 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.395 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.4 && secondPerc == 0.23) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.26;
    } else if (firstPerc == 0.31 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.315 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.32 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.325 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.33 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.335 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.34 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.345 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.35 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.355 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.36 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.365 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.37 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.375 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.38 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.93;
    } else if (firstPerc == 0.385 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.99;
    } else if (firstPerc == 0.39 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.395 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.4 && secondPerc == 0.235) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.19;
    } else if (firstPerc == 0.31 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.315 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.32 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.325 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.33 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.335 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.34 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.345 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.35 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.355 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.36 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.365 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.37 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.375 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.38 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.385 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.93;
    } else if (firstPerc == 0.39 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.395 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.06;
    } else if (firstPerc == 0.4 && secondPerc == 0.24) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.13;
    } else if (firstPerc == 0.31 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.315 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.32 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.325 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.33 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.335 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.34 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.345 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.35 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.355 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.36 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.365 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.37 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.375 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.38 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.8;
    } else if (firstPerc == 0.385 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.39 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.355 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.4 && secondPerc == 0.245) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2.07;
    } else if (firstPerc == 0.31 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.315 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.32 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.325 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.33 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.335 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.34 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.345 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.35 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.355 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.36 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.365 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.37 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.375 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.67;
    } else if (firstPerc == 0.38 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.385 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.8;
    } else if (firstPerc == 0.39 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.395 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.4 && secondPerc == 0.25) {
        document.querySelector(`.fouth-${id}`).innerHTML = 2;
    } else if (firstPerc == 0.31 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.315 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.32 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.325 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.33 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.335 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.34 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.345 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.35 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.355 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.36 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.365 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.37 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.375 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.38 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.67;
    } else if (firstPerc == 0.385 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.74;
    } else if (firstPerc == 0.39 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.395 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.87;
    } else if (firstPerc == 0.4 && secondPerc == 0.255) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.94;
    } else if (firstPerc == 0.31 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.315 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.32 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.325 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.33 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.335 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.34 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.345 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.35 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.355 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.36 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.365 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.37 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.375 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.38 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.385 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.67;
    } else if (firstPerc == 0.39 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.395 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.4 && secondPerc == 0.26) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.88;
    } else if (firstPerc == 0.315 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.32 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.325 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.33 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.335 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.34 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.345 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.35 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.355 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.36 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.365 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.37 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.375 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.38 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.385 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.61;
    } else if (firstPerc == 0.39 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.395 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.4 && secondPerc == 0.265) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.81;
    } else if (firstPerc == 0.32 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.325 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.33 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.335 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.34 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.345 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.35 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.355 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.36 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.365 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.37 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.375 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.38 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.385 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.39 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.395 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.4 && secondPerc == 0.27) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.75;
    } else if (firstPerc == 0.325 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.33 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.335 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.34 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.345 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.35 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.355 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.36 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.365 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.37 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.375 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.38 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.385 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.48;
    } else if (firstPerc == 0.39 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.395 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.4 && secondPerc == 0.275) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.68;
    } else if (firstPerc == 0.33 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.335 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.34 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.345 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.35 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.355 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.36 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.365 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.37 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.375 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.38 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.385 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.39 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.395 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.4 && secondPerc == 0.28) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.62;
    } else if (firstPerc == 0.335 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.34 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.345 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.35 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.355 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.36 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.365 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.37 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.375 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.38 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.385 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.39 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.395 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.4 && secondPerc == 0.285) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.55;
    } else if (firstPerc == 0.34 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.345 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.35 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.355 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.36 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.365 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.37 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.375 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.38 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.385 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.39 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.395 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.42;
    } else if (firstPerc == 0.4 && secondPerc == 0.29) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.49;
    } else if (firstPerc == 0.345 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.35 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.355 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.36 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.365 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.37 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.375 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.38 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.385 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.39 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.395 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.34;
    } else if (firstPerc == 0.4 && secondPerc == 0.295) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.43;
    } else if (firstPerc == 0.35 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.355 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.36 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.365 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.37 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.375 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.38 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.385 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.39 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.395 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.4 && secondPerc == 0.3) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.37;
    } else if (firstPerc == 0.355 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.36 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.365 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.37 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.375 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.38 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.385 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.39 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.395 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.2;
    } else if (firstPerc == 0.4 && secondPerc == 0.305) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.29;
    } else if (firstPerc == 0.36 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.365 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.37 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.375 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.38 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.385 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.39 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.395 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.4 && secondPerc == 0.31) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.22;
    } else if (firstPerc == 0.365 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.37 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.375 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.38 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.385 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.39 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.395 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.08;
    } else if (firstPerc == 0.4 && secondPerc == 0.315) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.15;
    } else if (firstPerc == 0.37 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.375 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.38 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.385 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.39 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.395 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.4 && secondPerc == 0.32) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.1;
    } else if (firstPerc == 0.375 && secondPerc == 0.325) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.38 && secondPerc == 0.325) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.385 && secondPerc == 0.325) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.39 && secondPerc == 0.325) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.395 && secondPerc == 0.325) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.96;
    } else if (firstPerc == 0.4 && secondPerc == 0.325) {
        document.querySelector(`.fouth-${id}`).innerHTML = 1.03;
    } else if (firstPerc == 0.38 && secondPerc == 0.33) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.385 && secondPerc == 0.33) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.39 && secondPerc == 0.33) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.395 && secondPerc == 0.33) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.4 && secondPerc == 0.33) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.97;
    } else if (firstPerc == 0.385 && secondPerc == 0.335) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.39 && secondPerc == 0.335) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.395 && secondPerc == 0.335) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.84;
    } else if (firstPerc == 0.4 && secondPerc == 0.335) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.91;
    } else if (firstPerc == 0.39 && secondPerc == 0.34) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.395 && secondPerc == 0.34) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.4 && secondPerc == 0.34) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.85;
    } else if (firstPerc == 0.395 && secondPerc == 0.345) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;
    } else if (firstPerc == 0.4 && secondPerc == 0.345) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.8;
    } else if (firstPerc == 0.4 && secondPerc == 0.35) {
        document.querySelector(`.fouth-${id}`).innerHTML = 0.74;

    } else if (a && (document.querySelector(`.fouth-${id}`).innerHTML = " ")) {
        document.querySelector(`.fouth-${id}`).innerHTML = "-";
    }
}




var table = document.querySelector("#items");

var isCalculating = false;

table.addEventListener("change", (e) => {
  if (isCalculating) return;
  
  const id = e.target.id;
  if (id.includes("choise")) {
    getSort(id.split("-")[1]);
  }
  if (id.includes("beforesush") || id.includes("aftersush")) {
    isCalculating = true;
    percent(id.split("-")[1]);
    isCalculating = false;
  }
  let firstx = document.getElementById("summ1-" + id.split("-")[1]).innerText;
  let secondx = document.getElementById("summ2-" + id.split("-")[1]).innerText;
  let thirdx = document.getElementById("summ3-" + id.split("-")[1]).value;
  console.log(firstx);
  console.log(secondx);
  console.log(thirdx);
  finalcount();
});








function addRow() {
    var table = document.querySelector("#items");
    var card = document.createElement("tr");
    card.id = table.childElementCount;

    card.innerHTML = `  <td class="">


    <select name="choise" id="choise-${table.childElementCount}" class="sort">
    <option class="after_sush" selected>Выбрать культуру</option>
                <option value="1"><p>Пшеница продовольственная, овес и ячмень продовольственные и кормовые</p></option>
                <option value="1.25"><p>Пшеница сильная, твёрдая и ценных сортов</p></option>
                <option value="1.66"><p>Ячмень поваренный</p></option>
                <option value="0.91"><p>Рожь</p></option>
                <option value="1.25" ><p>Просо</p></option>
                <option value="2"><p>Горох</p></option>
                <option value="0.8"><p>Гречиха</p></option>
                <option value="1.82">Кукуруза для крахмально-паточной промышленности</option>
                <option value="3.08">Кукуруза для пищеконцетратной промышленности</option>
                <option value="1.54">Кукуруза кормовая</option>
                <option value="2.5">Рис(зерно)</option>
            </select>


</td>
<td>


    <select name="before_sush" id="beforesush-${table.childElementCount}" class="sort" >
    <option class="after_sush" >-</option>
                        <option value="0.135" class="before_sush">13.5%</option>
                        <option value="0.140" class="before_sush">14%</option>
                        <option value="0.145" class="before_sush">14.5%</option>
                        <option value="0.15" class="before_sush">15%</option>
                        <option value="0.155" class="before_sush">15.5%</option>
                        <option value="0.16" class="before_sush">16%</option>
                        <option value="0.165" class="before_sush">16.5%</option>
                        <option value="0.17" class="before_sush">17%</option>
                        <option value="0.175" class="before_sush">17.5%</option>
                        <option value="0.18" class="before_sush">18%</option>
                        <option value="0.185" class="before_sush">18.5%</option>
                        <option value="0.190" class="before_sush">19%</option>
                        <option value="0.195" class="before_sush">19.5%</option>
                        <option value="0.2" class="before_sush">20%</option>
                        <option value="0.205" class="before_sush">20.5%</option>
                        <option value="0.21" class="before_sush">21%</option>
                        <option value="0.215" class="before_sush">21.5%</option>
                        <option value="0.22" class="before_sush">22%</option>
                        <option value="0.225" class="before_sush">22.5%</option>
                        <option value="0.23" class="before_sush">23%</option>
                        <option value="0.235" class="before_sush">23.5%</option>
                        <option value="0.24" class="before_sush">24%</option>
                        <option value="0.245" class="before_sush">24.5%</option>
                        <option value="0.25" class="before_sush">25%</option>
                        <option value="0.255" class="before_sush">25.5%</option>
                        <option value="0.26" class="before_sush">26%</option>
                        <option value="0.265" class="before_sush">26.5%</option>
                        <option value="0.27" class="before_sush">27%</option>
                        <option value="0.275" class="before_sush">27.5%</option>
                        <option value="0.28" class="before_sush">28%</option>
                        <option value="0.285" class="before_sush">28.5%</option>
                        <option value="0.29" class="before_sush">29%</option>
                        <option value="0.295" class="before_sush">29.5%</option>
                        <option value="0.3" class="before_sush">30%</option>
                        <option value="0.305" class="before_sush">30.5%</option>
                        <option value="0.31" class="before_sush">31%</option>
                        <option value="0.315" class="before_sush">31.5%</option>
                        <option value="0.32" class="before_sush">32%</option>
                        <option value="0.325" class="before_sush">32.5%</option>
                        <option value="0.33" class="before_sush">33%</option>
                        <option value="0.335" class="before_sush">33.5%</option>
                        <option value="0.34" class="before_sush">34%</option>
                        <option value="0.345" class="before_sush">34.5%</option>
                        <option value="0.35" class="before_sush">35%</option>
                        <option value="0.355" class="before_sush">35.5%</option>
                        <option value="0.36" class="before_sush">36%</option>
                        <option value="0.365" class="before_sush">36.5%</option>
                        <option value="0.37" class="before_sush">37%</option>
                        <option value="0.375" class="before_sush">37.5%</option>
                        <option value="0.38" class="before_sush">38%</option>
                        <option value="0.385" class="before_sush">38.5%</option>
                        <option value="0.39" class="before_sush">39%</option>
                        <option value="0.395" class="before_sush">39.5%</option>
                        <option value="0.4" class="before_sush">40%</option>
            </select>


</td>
<td>


    <select name="after_sush" id="aftersush-${table.childElementCount}" class="sort">
    <option class="after_sush" >-</option>
                
                <option class="after_sush" value="0.12">12%</option>
                <option class="after_sush" value="0.125">12.5%</option>
                <option class="after_sush" value="0.13">13%</option>
                <option class="after_sush" value="0.135">13.5%</option>
                <option class="after_sush" value="0.14">14%</option>
                <option class="after_sush" value="0.145">14.5%</option>
                <option class="after_sush" value="0.15">15%</option>
                <option class="after_sush" value="0.155">15.5%</option>
                <option class="after_sush" value="0.16">16%</option>
                <option class="after_sush" value="0.165">16.5%</option>
                <option class="after_sush" value="0.17">17%</option>
                <option class="after_sush" value="0.175">17.5%</option>
                <option class="after_sush" value="0.18">18%</option>
                <option class="after_sush" value="0.185">18.5%</option>
                <option class="after_sush" value="0.19">19%</option>
                <option class="after_sush" value="0.195">19.5%</option>
                <option class="after_sush" value="0.2">20%</option>
                <option class="after_sush" value="0.205">20.5%</option>
                <option class="after_sush" value="0.21">21%</option>
                <option class="after_sush" value="0.215">21.5%</option>
                <option class="after_sush" value="0.22">22%</option>
                <option class="after_sush" value="0.225">22.5%</option>
                <option class="after_sush" value="0.23">23%</option>
                <option class="after_sush" value="0.235">23.5%</option>
                <option class="after_sush" value="0.24">24%</option>
                <option class="after_sush" value="0.245">24.5%</option>
                <option class="after_sush" value="0.25">25%</option>
                <option class="after_sush" value="0.255">25.5%</option>
                <option class="after_sush" value="0.26">26%</option>
                <option class="after_sush" value="0.265">26.5%</option>
                <option class="after_sush" value="0.27">27%</option>
                <option class="after_sush" value="0.275">27.5%</option>
                <option class="after_sush" value="0.28">28%</option>
                <option class="after_sush" value="0.285">28.5%</option>
                <option class="after_sush" value="0.29">29%</option>
                <option class="after_sush" value="0.295">29.5%</option>
                <option class="after_sush" value="0.3">30%</option>
                <option class="after_sush" value="0.305">30.5%</option>
                <option class="after_sush" value="0.31">31%</option>
                <option class="after_sush" value="0.315">31.5%</option>
                <option class="after_sush" value="0.32">32%</option>
                <option class="after_sush" value="0.325">32.5%</option>
                <option class="after_sush" value="0.33">33%</option>
                <option class="after_sush" value="0.335">33.5%</option>
                <option class="after_sush" value="0.34">34%</option>
                <option class="after_sush" value="0.345">34.5%</option>
                <option class="after_sush" value="0.35">35%</option>
            </select>


</td>
<td class="fouth-${table.childElementCount} " id="summ1-${table.childElementCount}"  ></td>
<td class="fivth-${table.childElementCount}" id="summ2-${table.childElementCount}"></td>
<td><input type="text" class = "inputtn" id="summ3-${table.childElementCount}"></td>
<td id="itog-${table.childElementCount}"> </td>
</tr>
<tr>
`;
    table.appendChild(card);
}

function finalcount() {
    //alert('Проверка'+'oo');
    /*let firstx = document.getElementById("summ1").innerText;
    let secondx = document.getElementById("summ2").innerText;
    let thirdx = document.getElementById("summ3").value;
    let finalcalc = document.querySelector(".final_summ");
    console.log(firstx);
    console.log(secondx);
    console.log(thirdx);
    let summa = +firstx * +secondx * +thirdx;
    console.log(+firstx * +secondx * +thirdx);
    finalcalc.innerHTML = summa;*/



    /*let stroki = document.getElementById("items").getElementsByTagName('tr');

    for (let stroka of stroki) {
    	let parent = document.querySelector(stroka);
    	let elems = parent.querySelectorAll('#summ1');
    	alert(elems);
    	//alert(stroka.getElementById("summ1").innerText);
    }*/

    var table = document.getElementById("items");
    let finalcalc = document.querySelector(".final_summ");
    let summa = 0;
    for (var i = 1, row; row = table.rows[i]; i++) {
        /*  var itog = document.getElementById("itog-" + (i + 1));
         itog = document.getElementById("summ1-" + (i + 1)).innerText * +document.getElementById("summ2-" + (i + 1)).innerText * +document.getElementById("summ3-" + (i + 1)).value */
        /*for (var j = 0, col; col = row.cells[j]; j++) {
			alert(col.innerHTML);
	   }  */
        /*if (row.cells[3] && row.cells[4] && row.cells[5]) {
			alert(row.cells[3].innerHTML + " | " + row.cells[4].innerHTML + " | " + document.getElementById("summ3-"+(i+1)).value);
	    }*/
        if (document.getElementById("summ1-" + (i + 1)) && document.getElementById("summ2-" + (i + 1)) && document.getElementById("summ3-" + (i + 1)).value) {
            //alert (document.getElementById("summ1-"+(i+1)).innerText  + " | " +  document.getElementById("summ2-"+(i+1)).innerText  + " | " + document.getElementById("summ3-"+(i+1)).value);
            itog = document.getElementById("summ1-" + (i + 1)).innerText * +document.getElementById("summ2-" + (i + 1)).innerText * +document.getElementById("summ3-" + (i + 1)).value;
            summa = summa + document.getElementById("summ1-" + (i + 1)).innerText * +document.getElementById("summ2-" + (i + 1)).innerText * +document.getElementById("summ3-" + (i + 1)).value;
            document.getElementById("itog-" + (i + 1)).innerHTML = itog.toFixed(1);
        }
        //alert(row[i].getElementById("summ1").innerText);
    }
    finalcalc.innerHTML = summa.toFixed(1);

    /*for (var stroka = 1; stroka < stroki.length; stroka++) {
    	alert(stroka);
    	alert (document.getElementsByClassName("fouth-"+stroka).innerText);
    }*/

}

function eee() {
    var table = document.getElementById("items");
    var trs = document.querySelectorAll('tr');
    for (var i = 1; i < trs.length; i++) {
        var tds = trs[i].querySelectorAll('td');
        var sum = 0;
        for (var j = 3; j < tds.length; j++) {
            sum *= Number(tds[j].innerText);
            console.log([j].innerHTML);
            console.log(sum);
        }
    }
}

function bbb() {
    let firstx = document.getElementById("summ1").innerText;
    let secondx = document.getElementById("summ2").innerText;
    let thirdx = document.getElementById("summ3").value;
    let finalcalc = document.querySelector(".final_summ");

    var table = document.getElementById("items");
    var trs = document.querySelectorAll('tr');
    for (var i = 1; i < trs.length - 1; i++) {
        var tds = trs[i].querySelectorAll('td');

        for (var j = 3; j < tds.length; j++) {

            console.log([j]);

        }
    }
}