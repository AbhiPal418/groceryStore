
function openOrderModal(orderId) {
    // 1. Set the Order ID in the header
    document.getElementById('modal-order-id').innerText = orderId;

    // 2. Get the hidden items from the row
    const hiddenItems = document.getElementById('items-' + orderId).innerHTML;

    // 3. Inject them into the modal list
    document.getElementById('modal-items-list').innerHTML = hiddenItems;

    // 4. Show the modal
    document.getElementById('orderModal').style.display = 'block';
}

function closeOrderModal() {
    document.getElementById('orderModal').style.display = 'none';
}

// Close modal if user clicks outside of the white box
window.onclick = function(event) {
    const modal = document.getElementById('orderModal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
