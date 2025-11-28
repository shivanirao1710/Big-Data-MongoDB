// minimal script — can expand for AJAX cart, etc.
document.addEventListener('DOMContentLoaded', function(){
  // Example: hide flash messages after 4s
  setTimeout(function(){
    const flashes = document.querySelectorAll('.flash-list');
    flashes.forEach(f => f.style.display = 'none');
  }, 4000);
});
