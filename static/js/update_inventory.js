function add() {
    let input = document.getElementById("newvalid");
    let newNum = document.getElementById("DriverInventory"); 
    let newinput = parseInt(input.value);
    let newNuminput = parseInt(newNum.textContent)
    newNum.textContent = newNuminput +1; 
    input.value = newinput+1;
};

function subtract() {
    let input = document.getElementById("newvalid");
    let newNum = document.getElementById("DriverInventory"); 
    let newinput = parseInt(input.value);
    let newNuminput = parseInt(newNum.textContent)
    newNum.textContent = newNuminput -1 ;
    input.value = newinput-1;
};