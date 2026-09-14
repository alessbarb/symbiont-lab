function toggleDrawer(id, open) { const drawer = document.querySelector(id); drawer.classList.toggle("open", open); drawer.setAttribute("aria-hidden", String(!open)); }

export { toggleDrawer };
