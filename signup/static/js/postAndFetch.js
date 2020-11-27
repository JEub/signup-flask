let projectList = d3.select('#mainProjectList')

function updateProjects(element){
    var projects = fetch('/projects/all')
        .then(res => res.json())
        .then(data => projects = data);;
    element.append('li').append('a')
        .attr('href', `/projects/${projects.project_name}`)
        .text(projects.project_name);
}

updateProjects(projectList);