
let projectList = d3.select('#mainProjectList');
let projects = [];
fetch('/projects/all')
    .then(res => res.json())
    .then(data => projects = data);

projects.forEach(function(project) {
    console.log(project);
    projectList.append('li').append('a').text(project.project_name);
    });
        //.attr('xlink:href', `/projects/${project.project_name}`)
