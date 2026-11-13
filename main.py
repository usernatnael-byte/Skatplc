from fastapi import FastAPI, HTTPException
from database import db
from models import ItemModel

app = FastAPI(title="FastAPI Firebase Firestore Render App")

@app.get("/")
def read_root():
    return {"message": "አፕሊኬሽኑ በ Firebase Firestore እና በ Render ላይ በትክክል እየሰራ ነው!"}

# 1. መረጃ መመዝገብ (Create Item)
@app.post("/items/")
def create_item(item: ItemModel):
    try:
        # 'items' የሚባል ኮሌክሽን ውስጥ መረጃውን እናስገባለን
        doc_ref = db.collection("items").document()
        item_dict = item.dict()
        doc_ref.set(item_dict)
        
        return {
            "status": "success",
            "id": doc_ref.id,
            "data": item_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. ሁሉንም መረጃዎች ማንበብ (Get All Items)
@app.get("/items/")
def get_items():
    try:
        items_ref = db.collection("items")
        docs = items_ref.stream()
        
        items_list = []
        for doc in docs:
            item_data = doc.to_dict()
            item_data["id"] = doc.id
            items_list.append(item_data)
            
        return items_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. አንድን መረጃ በ ID ፈልጎ ማምጣት (Get Item by ID)
@app.get("/items/{item_id}")
def get_item(item_id: str):
    try:
        doc_ref = db.collection("items").document(item_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="መረጃው አልተገኘም (Item not found)")
            
        item_data = doc.to_dict()
        item_data["id"] = doc.id
        return item_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. መረጃን ማጥፋት (Delete Item)
@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    try:
        doc_ref = db.collection("items").document(item_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="መረጃው አልተገኘም")
            
        doc_ref.delete()
        return {"status": "success", "message": f"የዕቃ ቁጥር {item_id} ሰርቷል/ጠፍቷል"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
