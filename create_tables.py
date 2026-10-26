
from app.database.session import Base, engine
from app.models import (Employee, CDREhrmsUpload, EhrmsWorkflowRequest, EhrmsWorkflowRequestArchive,)

Base.metadata.create_all(bind=engine)

print("All tables created successfully.")
