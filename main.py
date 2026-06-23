pageItems.forEach((item) => {

    // 🚨 就是加在這裡
    if (!item.url) return;

    const cleanTitle = item.title
        .replace(/'/g, "&apos;")
        .replace(/"/g, "&quot;");

    resBox.innerHTML += `
        <div class="song-item">
            <span style="max-width:75%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                ${item.title}
            </span>
            <button onclick="addSong('${cleanTitle}', '${item.url}')">➕ 加入</button>
        </div>
    `;
});
