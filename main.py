import os
import asyncpg

from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Path, Header
from pydantic import BaseModel, Field, EmailStr, field_validator

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    try:
        conn = await asyncpg.connect(DATABASE_URL)

        await conn.execute(
            """
            SELECT 1
            FROM agent
            LIMIT 1
            """
        )

        await conn.close()

        print("Connected to PostgreSQL database")

    except Exception as e:
        print(f"Database connection failed: {e}")

    yield


app = FastAPI(
    title="EstateFlow API",
    description="FastAPI backend for Agent, Project, and Assignment management",
    version="1.0.0",
    lifespan=lifespan
)


async def get_connection():
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_CONFIGURATION_ERROR",
                "message": "DATABASE_URL is not configured."
            }
        )

    try:
        return await asyncpg.connect(DATABASE_URL)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_CONNECTION_ERROR",
                "message": "Unable to connect to the database."
            }
        )


class AgentCreate(BaseModel):
    agent_name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    email: EmailStr

    contact_number: str | None = Field(
        default=None,
        max_length=20
    )

    status: str = Field(
        default="Active",
        max_length=20
    )

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Agent name cannot be empty")

        return value

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            return None

        return value

    @field_validator("status")
    @classmethod
    def validate_agent_status(cls, value):
        value = value.strip()

        if value not in ["Active", "Inactive"]:
            raise ValueError(
                "Status must be Active or Inactive"
            )

        return value


class AgentUpdate(BaseModel):
    agent_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    email: EmailStr | None = None

    contact_number: str | None = Field(
        default=None,
        max_length=20
    )

    status: str | None = Field(
        default=None,
        max_length=20
    )

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Agent name cannot be empty")

        return value

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value):
        if value is None:
            return value

        value = value.strip()

        return value if value else None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is None:
            return value

        value = value.strip()

        if value not in ["Active", "Inactive"]:
            raise ValueError(
                "Status must be Active or Inactive"
            )

        return value


class ProjectCreate(BaseModel):
    project_name: str = Field(
        ...,
        min_length=2,
        max_length=150
    )

    location: str = Field(
        ...,
        min_length=2,
        max_length=150
    )

    project_type: str = Field(
        ...,
        min_length=2,
        max_length=50
    )

    project_details: str | None = None

    @field_validator(
        "project_name",
        "location",
        "project_type",
        "project_details"
    )
    @classmethod
    def clean_text(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty")

        return value


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150
    )

    location: str | None = Field(
        default=None,
        min_length=2,
        max_length=150
    )

    project_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=50
    )

    project_details: str | None = None

    @field_validator(
        "project_name",
        "location",
        "project_type",
        "project_details"
    )
    @classmethod
    def clean_text(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty")

        return value


class AssignmentCreate(BaseModel):
    agent_id: int = Field(
        ...,
        gt=0
    )

    project_id: int = Field(
        ...,
        gt=0
    )

    status: str = Field(
        default="Planning",
        max_length=30
    )

    assigned_date: date | None = None
    status_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        value = value.strip()

        allowed_statuses = [
            "Planning",
            "Ongoing",
            "Completed",
            "On Hold",
            "Cancelled"
        ]

        if value not in allowed_statuses:
            raise ValueError(
                "Invalid assignment status"
            )

        return value


class AssignmentUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        max_length=30
    )

    assigned_date: date | None = None
    status_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is None:
            return value

        value = value.strip()

        allowed_statuses = [
            "Planning",
            "Ongoing",
            "Completed",
            "On Hold",
            "Cancelled"
        ]

        if value not in allowed_statuses:
            raise ValueError(
                "Invalid assignment status"
            )

        return value


@app.get("/api/health")
async def health_check():

    conn = await get_connection()

    try:
        await conn.execute("SELECT 1")

        return {
            "status": "success",
            "message": "API and database are running"
        }

    finally:
        await conn.close()


@app.post("/api/auth/login")
async def login(
    email: EmailStr,
    password: str
):
    if not password:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_CREDENTIALS",
                "message": "Email or password is incorrect."
            }
        )

    conn = await get_connection()

    try:
        user = await conn.fetchrow(
            """
            SELECT agent_id, agent_name, email, status
            FROM agent
            WHERE email = $1
            """,
            email
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "INVALID_CREDENTIALS",
                    "message": "Email or password is incorrect."
                }
            )

        if user["status"] != "Active":
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "ACCOUNT_INACTIVE",
                    "message": "This account is inactive."
                }
            )

        return {
            "status": "success",
            "message": "Login successful.",
            "data": {
                "agent_id": user["agent_id"],
                "agent_name": user["agent_name"],
                "email": user["email"]
            }
        }

    finally:
        await conn.close()


@app.post("/api/agents", status_code=201)
async def create_agent(agent: AgentCreate):

    conn = await get_connection()

    try:
        existing = await conn.fetchval(
            """
            SELECT agent_id
            FROM agent
            WHERE email = $1
            """,
            agent.email
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "DUPLICATE_EMAIL",
                    "message": "An agent with this email already exists."
                }
            )

        row = await conn.fetchrow(
            """
            INSERT INTO agent
                (
                    agent_name,
                    email,
                    contact_number,
                    status
                )
            VALUES
                ($1, $2, $3, $4)
            RETURNING
                agent_id,
                agent_name,
                email,
                contact_number,
                status,
                date_registered
            """,
            agent.agent_name,
            agent.email,
            agent.contact_number,
            agent.status
        )

        return {
            "status": "success",
            "message": "Agent created successfully.",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "DUPLICATE_EMAIL",
                "message": "An agent with this email already exists."
            }
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to create agent."
            }
        )

    finally:
        await conn.close()


@app.get("/api/agents")
async def get_agents(
    status: str | None = Query(
        default=None,
        min_length=1,
        max_length=20
    )
):

    if status and status not in ["Active", "Inactive"]:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_STATUS",
                "message": "Status must be Active or Inactive."
            }
        )

    conn = await get_connection()

    try:
        if status:
            rows = await conn.fetch(
                """
                SELECT *
                FROM agent
                WHERE status = $1
                ORDER BY agent_id
                """,
                status
            )
        else:
            rows = await conn.fetch(
                """
                SELECT *
                FROM agent
                ORDER BY agent_id
                """
            )

        return {
            "status": "success",
            "count": len(rows),
            "data": [dict(row) for row in rows]
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to retrieve agents."
            }
        )

    finally:
        await conn.close()


@app.get("/api/agents/{agent_id}")
async def get_agent(
    agent_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            SELECT *
            FROM agent
            WHERE agent_id = $1
            """,
            agent_id
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "AGENT_NOT_FOUND",
                    "message": "Agent does not exist."
                }
            )

        return {
            "status": "success",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to retrieve agent."
            }
        )

    finally:
        await conn.close()


@app.put("/api/agents/{agent_id}")
async def update_agent(
    agent: AgentUpdate,
    agent_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        existing = await conn.fetchrow(
            """
            SELECT *
            FROM agent
            WHERE agent_id = $1
            """,
            agent_id
        )

        if not existing:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "AGENT_NOT_FOUND",
                    "message": "Agent does not exist."
                }
            )

        updated_name = (
            agent.agent_name
            if agent.agent_name is not None
            else existing["agent_name"]
        )

        updated_email = (
            agent.email
            if agent.email is not None
            else existing["email"]
        )

        updated_contact = (
            agent.contact_number
            if agent.contact_number is not None
            else existing["contact_number"]
        )

        updated_status = (
            agent.status
            if agent.status is not None
            else existing["status"]
        )

        row = await conn.fetchrow(
            """
            UPDATE agent
            SET
                agent_name = $1,
                email = $2,
                contact_number = $3,
                status = $4
            WHERE agent_id = $5
            RETURNING *
            """,
            updated_name,
            updated_email,
            updated_contact,
            updated_status,
            agent_id
        )

        return {
            "status": "success",
            "message": "Agent updated successfully.",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "DUPLICATE_EMAIL",
                "message": "The email is already registered."
            }
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to update agent."
            }
        )

    finally:
        await conn.close()


@app.delete("/api/agents/{agent_id}")
async def delete_agent(
    agent_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            DELETE FROM agent
            WHERE agent_id = $1
            RETURNING agent_id
            """,
            agent_id
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "AGENT_NOT_FOUND",
                    "message": "Agent does not exist."
                }
            )

        return {
            "status": "success",
            "message": "Agent deleted successfully.",
            "agent_id": row["agent_id"]
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to delete agent."
            }
        )

    finally:
        await conn.close()


@app.post("/api/projects", status_code=201)
async def create_project(project: ProjectCreate):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            INSERT INTO project
                (
                    project_name,
                    location,
                    project_type,
                    project_details
                )
            VALUES
                ($1, $2, $3, $4)
            RETURNING *
            """,
            project.project_name,
            project.location,
            project.project_type,
            project.project_details
        )

        return {
            "status": "success",
            "message": "Project created successfully.",
            "data": dict(row)
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to create project."
            }
        )

    finally:
        await conn.close()


@app.get("/api/projects")
async def get_projects(
    project_type: str | None = Query(
        default=None,
        min_length=1,
        max_length=50
    )
):

    conn = await get_connection()

    try:
        if project_type:
            rows = await conn.fetch(
                """
                SELECT *
                FROM project
                WHERE project_type = $1
                ORDER BY project_id
                """,
                project_type
            )
        else:
            rows = await conn.fetch(
                """
                SELECT *
                FROM project
                ORDER BY project_id
                """
            )

        return {
            "status": "success",
            "count": len(rows),
            "data": [dict(row) for row in rows]
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to retrieve projects."
            }
        )

    finally:
        await conn.close()


@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            SELECT *
            FROM project
            WHERE project_id = $1
            """,
            project_id
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "PROJECT_NOT_FOUND",
                    "message": "Project does not exist."
                }
            )

        return {
            "status": "success",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to retrieve project."
            }
        )

    finally:
        await conn.close()


@app.put("/api/projects/{project_id}")
async def update_project(
    project: ProjectUpdate,
    project_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        existing = await conn.fetchrow(
            """
            SELECT *
            FROM project
            WHERE project_id = $1
            """,
            project_id
        )

        if not existing:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "PROJECT_NOT_FOUND",
                    "message": "Project does not exist."
                }
            )

        project_name = (
            project.project_name
            if project.project_name is not None
            else existing["project_name"]
        )

        location = (
            project.location
            if project.location is not None
            else existing["location"]
        )

        project_type = (
            project.project_type
            if project.project_type is not None
            else existing["project_type"]
        )

        project_details = (
            project.project_details
            if project.project_details is not None
            else existing["project_details"]
        )

        row = await conn.fetchrow(
            """
            UPDATE project
            SET
                project_name = $1,
                location = $2,
                project_type = $3,
                project_details = $4
            WHERE project_id = $5
            RETURNING *
            """,
            project_name,
            location,
            project_type,
            project_details,
            project_id
        )

        return {
            "status": "success",
            "message": "Project updated successfully.",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to update project."
            }
        )

    finally:
        await conn.close()


@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            DELETE FROM project
            WHERE project_id = $1
            RETURNING project_id
            """,
            project_id
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "PROJECT_NOT_FOUND",
                    "message": "Project does not exist."
                }
            )

        return {
            "status": "success",
            "message": "Project deleted successfully.",
            "project_id": row["project_id"]
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to delete project."
            }
        )

    finally:
        await conn.close()


@app.post("/api/assignments", status_code=201)
async def create_assignment(
    assignment: AssignmentCreate
):

    conn = await get_connection()

    try:
        agent_exists = await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                FROM agent
                WHERE agent_id = $1
            )
            """,
            assignment.agent_id
        )

        if not agent_exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "AGENT_NOT_FOUND",
                    "message": "The specified agent does not exist."
                }
            )

        project_exists = await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                FROM project
                WHERE project_id = $1
            )
            """,
            assignment.project_id
        )

        if not project_exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "PROJECT_NOT_FOUND",
                    "message": "The specified project does not exist."
                }
            )

        duplicate = await conn.fetchval(
            """
            SELECT assignment_id
            FROM assignment
            WHERE agent_id = $1
            AND project_id = $2
            """,
            assignment.agent_id,
            assignment.project_id
        )

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "DUPLICATE_ASSIGNMENT",
                    "message": "This agent is already assigned to this project."
                }
            )

        assigned_date = (
            assignment.assigned_date
            if assignment.assigned_date
            else date.today()
        )

        status_date = (
            assignment.status_date
            if assignment.status_date
            else date.today()
        )

        row = await conn.fetchrow(
            """
            INSERT INTO assignment
                (
                    agent_id,
                    project_id,
                    status,
                    assigned_date,
                    status_date
                )
            VALUES
                ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            assignment.agent_id,
            assignment.project_id,
            assignment.status,
            assigned_date,
            status_date
        )

        return {
            "status": "success",
            "message": "Assignment created successfully.",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "DUPLICATE_ASSIGNMENT",
                "message": "This agent is already assigned to this project."
            }
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to create assignment."
            }
        )

    finally:
        await conn.close()


@app.get("/api/assignments")
async def get_assignments(
    status: str | None = Query(
        default=None,
        max_length=30
    )
):

    allowed_statuses = [
        "Planning",
        "Ongoing",
        "Completed",
        "On Hold",
        "Cancelled"
    ]

    if status and status not in allowed_statuses:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_STATUS",
                "message": "Invalid assignment status."
            }
        )

    conn = await get_connection()

    try:
        if status:
            rows = await conn.fetch(
                """
                SELECT
                    a.assignment_id,
                    a.agent_id,
                    ag.agent_name,
                    a.project_id,
                    p.project_name,
                    a.status,
                    a.assigned_date,
                    a.status_date
                FROM assignment a
                INNER JOIN agent ag
                    ON a.agent_id = ag.agent_id
                INNER JOIN project p
                    ON a.project_id = p.project_id
                WHERE a.status = $1
                ORDER BY a.assignment_id
                """,
                status
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    a.assignment_id,
                    a.agent_id,
                    ag.agent_name,
                    a.project_id,
                    p.project_name,
                    a.status,
                    a.assigned_date,
                    a.status_date
                FROM assignment a
                INNER JOIN agent ag
                    ON a.agent_id = ag.agent_id
                INNER JOIN project p
                    ON a.project_id = p.project_id
                ORDER BY a.assignment_id
                """
            )

        return {
            "status": "success",
            "count": len(rows),
            "data": [dict(row) for row in rows]
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to retrieve assignments."
            }
        )

    finally:
        await conn.close()


@app.get("/api/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            SELECT
                a.assignment_id,
                a.agent_id,
                ag.agent_name,
                a.project_id,
                p.project_name,
                a.status,
                a.assigned_date,
                a.status_date
            FROM assignment a
            INNER JOIN agent ag
                ON a.agent_id = ag.agent_id
            INNER JOIN project p
                ON a.project_id = p.project_id
            WHERE a.assignment_id = $1
            """,
            assignment_id
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "ASSIGNMENT_NOT_FOUND",
                    "message": "Assignment does not exist."
                }
            )

        return {
            "status": "success",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to retrieve assignment."
            }
        )

    finally:
        await conn.close()


@app.put("/api/assignments/{assignment_id}")
async def update_assignment(
    assignment: AssignmentUpdate,
    assignment_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        existing = await conn.fetchrow(
            """
            SELECT *
            FROM assignment
            WHERE assignment_id = $1
            """,
            assignment_id
        )

        if not existing:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "ASSIGNMENT_NOT_FOUND",
                    "message": "Assignment does not exist."
                }
            )

        updated_status = (
            assignment.status
            if assignment.status is not None
            else existing["status"]
        )

        updated_assigned_date = (
            assignment.assigned_date
            if assignment.assigned_date is not None
            else existing["assigned_date"]
        )

        updated_status_date = (
            assignment.status_date
            if assignment.status_date is not None
            else existing["status_date"]
        )

        row = await conn.fetchrow(
            """
            UPDATE assignment
            SET
                status = $1,
                assigned_date = $2,
                status_date = $3
            WHERE assignment_id = $4
            RETURNING *
            """,
            updated_status,
            updated_assigned_date,
            updated_status_date,
            assignment_id
        )

        return {
            "status": "success",
            "message": "Assignment updated successfully.",
            "data": dict(row)
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to update assignment."
            }
        )

    finally:
        await conn.close()


@app.delete("/api/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int = Path(
        ...,
        gt=0
    )
):

    conn = await get_connection()

    try:
        row = await conn.fetchrow(
            """
            DELETE FROM assignment
            WHERE assignment_id = $1
            RETURNING assignment_id
            """,
            assignment_id
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "ASSIGNMENT_NOT_FOUND",
                    "message": "Assignment does not exist."
                }
            )

        return {
            "status": "success",
            "message": "Assignment deleted successfully.",
            "assignment_id": row["assignment_id"]
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Unable to delete assignment."
            }
        )

    finally:
        await conn.close()