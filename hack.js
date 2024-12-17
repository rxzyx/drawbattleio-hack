// ==UserScript==
// @name         Draw Battle IO Hack
// @namespace    https://github.com/rxzyx/
// @version      1.0
// @description  A UserScript for Draw Battle.
// @author       rxzyx (rzx)
// @match        https://drawbattle.io/*
// @icon         https://drawbattle.io/favicon.png
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    const n = n => n + ['th', 'st', 'nd', 'rd'][(n % 10 === 1 && n % 100 !== 11) ? 1 : (
        n % 10 === 2 && n % 100 !== 12) ? 2 : (n % 10 === 3 && n % 100 !== 13) ? 3 : 0];
    var reactedWordDashes = "_redactedWordDashes_1izay_24"
    var showdown_info = {
        index: 0,
        team: 0,
        wordlist: []
    }
    var game_info = {}
    var my_team = []

    function setText(textContent, wait=1000) {
        setTimeout(function() {
            const innerDiv = document.createElement('div');
            const parentDiv = document.querySelector('div[class*="paneHeader"]');
            if (parentDiv) {
                if (innerDiv) {
                    innerDiv.textContent = textContent
                } else {
                    innerDiv.className = reactedWordDashes
                    innerDiv.setAttribute('bis_skin_checked', '1');
                    innerDiv.textContent = textContent
                    parentDiv.appendChild(innerDiv)
                }
            } else {
                alert(textContent)
            }
        }, wait)
    }

    const OriginalWebsocket = window.WebSocket
    const ProxiedWebSocket = function() {
        const ws = new OriginalWebsocket(...arguments)
        window.websocket = ws;
        ws.addEventListener("message", function (e) {
            const ps = JSON.parse(e.data)
            console.log(ps, typeof ps, ps.length, ps[0])
            if (ps && typeof ps === "object") {
                switch(ps[0]) {
                    case 6:
                        var nameInput = document.getElementById("nameInput")
                        if (nameInput) nameInput.removeAttribute("maxLength");
                        break;
                    case 8:
                        if (ps.length == 4) {
                            console.log(`The ${n(ps[1] + 1)} is ${ps[2]}`)
                            var wordClass = document.querySelector('[class*="redactedWordDashes"]')
                            reactedWordDashes = wordClass.className
                            if (wordClass) wordClass.textContent = ps[2]
                        }
                        break;
                    case 15:
                        if (ps.length == 2) {
                            showdown_info.wordlist = ps[1].words
                            console.log(`The wordlist is: ${ps[1].words}`)
                        }
                        break;
                    case 16:
                        if (ps.length == 4) {
                            // if (ps[3].drawerId == sessionStorage.getItem('userId')) {
                            if (my_team && my_team.includes(ps[3].drawerId)) {
                                showdown_info.index = ps[1]
                                showdown_info.team = ps[2]
                                if (ps[3].drawerId != sessionStorage.getItem('userId')) {
                                    setTimeout(function() {
                                        if (!document.querySelector('[class*="redactedWordDashes"]')) {
                                            setText(`${showdown_info.wordlist[showdown_info.index]}`, 0)
                                        } else {
                                            document.querySelector(
                                                '[class*="redactedWordDashes"]'
                                            ).textContent = `${showdown_info.wordlist[showdown_info.index]}`
                                        }
                                    }, 1000)
                                }
                            }
                        }
                        break;
                    case 5:
                        if (ps.length == 4) {
                            setText(`Choices: ${ps[2].wordChoices}`)
                            console.log(`The wordchoices are: ${ps[2].wordChoices}`)
                        }
                        break;
                    case 3:
                        if (ps.length == 4 && typeof ps[1] == "object") {
                            // if (ps[3].userId == sessionStorage.getItem('userId')) {
                            if (my_team && my_team.includes(ps[3].userId)) {
                                showdown_info.index = ps[1][0]
                                showdown_info.team = ps[2]
                            }
                        }
                        break;
                    case 1:
                        if (ps.length == 3 && ps[0] == 1) {
                            game_info = ps[1]
                            showdown_info.team = game_info.teams.findIndex(x => x.userIds.includes(sessionStorage.getItem('userId')))
                            my_team = game_info.teams[showdown_info.team].userIds
                            if (game_info.finalRound) {
                                showdown_info = {
                                    index: game_info.finalRound.teamStates[showdown_info.team].length - 1,
                                    team: showdown_info.team,
                                    wordlist: game_info.finalRound.words
                                }
                                setText(`${showdown_info.wordlist[showdown_info.index]}`)
                            } else if (game_info.currentRound) {
                                if (game_info.currentRound.word) {
                                    setText(`${game_info.currentRound.word}`)
                                } else {
                                    setText(`Choices: ${game_info.currentRound.wordChoices[0]}`)
                                }
                            }
                        }
                        break;

                    default:
                        break;
                }
            }
        })
        return ws;
    };
    window.WebSocket = ProxiedWebSocket;
})();
