DROP TABLE IF EXISTS assignment;
DROP TABLE IF EXISTS project;
DROP TABLE IF EXISTS agent;

CREATE TABLE agent (
    agent_id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    contact_number VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    date_registered DATE NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT chk_agent_status
        CHECK (status IN ('Active', 'Inactive'))
);

CREATE TABLE project (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL,
    location VARCHAR(150) NOT NULL,
    project_type VARCHAR(50) NOT NULL,
    project_details TEXT,
    created_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE assignment (
    assignment_id SERIAL PRIMARY KEY,
    agent_id INT NOT NULL,
    project_id INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Planning',
    assigned_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status_date DATE NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT fk_assignment_agent
        FOREIGN KEY (agent_id)
        REFERENCES agent(agent_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_assignment_project
        FOREIGN KEY (project_id)
        REFERENCES project(project_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT chk_assignment_status
        CHECK (
            status IN (
                'Planning',
                'Ongoing',
                'Completed',
                'On Hold',
                'Cancelled'
            )
        ),

    CONSTRAINT unique_agent_project
        UNIQUE (agent_id, project_id)
);

CREATE INDEX idx_assignment_agent_id
ON assignment(agent_id);

CREATE INDEX idx_assignment_project_id
ON assignment(project_id);

INSERT INTO agent
    (agent_name, email, contact_number, status)
VALUES
    ('Juan', 'juan@email.com', '09123456789', 'Active'),
    ('Maria', 'maria@email.com', '09987654321', 'Active');

INSERT INTO project
    (project_name, location, project_type, project_details)
VALUES
    ('Cebu House', 'Cebu', 'Residential', 'House development'),
    ('Mactan Villa', 'Lapu-Lapu', 'Residential', 'Villa development'),
    ('Banilad House', 'Cebu', 'Residential', 'Housing development');

INSERT INTO assignment
    (agent_id, project_id, status, assigned_date, status_date)
VALUES
    (1, 1, 'Ongoing', '2026-08-01', '2026-08-01'),
    (1, 2, 'Planning', '2026-08-05', '2026-08-05'),
    (2, 3, 'Completed', '2026-08-06', '2026-08-06');