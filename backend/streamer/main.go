package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/anacrolix/torrent"
)

var client *torrent.Client

func main() {
	tmpDir := filepath.Join(os.TempDir(), "go-streamer-cache")
	os.RemoveAll(tmpDir)
	os.MkdirAll(tmpDir, 0777)

	cfg := torrent.NewDefaultClientConfig()
	cfg.DataDir = tmpDir

	var err error
	client, err = torrent.NewClient(cfg)
	if err != nil {
		log.Fatalf("Error starting torrent client: %v", err)
	}
	defer client.Close()

	http.HandleFunc("/stream", streamHandler)
	http.HandleFunc("/status", statusHandler)

	fmt.Println("[Go Streamer] Listening on port 8767")
	log.Fatal(http.ListenAndServe(":8767", nil))
}

func statusHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	magnet := r.URL.Query().Get("magnet")
	if magnet == "" {
		http.Error(w, "Missing magnet", http.StatusBadRequest)
		return
	}

	t, err := client.AddMagnet(magnet)
	if err != nil {
		http.Error(w, "Failed to add magnet", http.StatusInternalServerError)
		return
	}

	hasMetadata := t.Info() != nil
	peers := len(t.PeerConns())
	
	statusMsg := "Connecting to Swarm (DHT)..."
	if peers > 0 {
		statusMsg = fmt.Sprintf("Connected to %d Peers... Fetching Metadata", peers)
	}
	if hasMetadata {
		statusMsg = "Metadata found! Buffering video stream..."
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": statusMsg,
		"peers": peers,
		"hasMetadata": hasMetadata,
		"name": t.Name(),
	})
}

func streamHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	magnet := r.URL.Query().Get("magnet")
	if magnet == "" {
		http.Error(w, "Missing magnet", http.StatusBadRequest)
		return
	}

	t, err := client.AddMagnet(magnet)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	select {
	case <-t.GotInfo():
	case <-time.After(60 * time.Second):
		http.Error(w, "Timeout getting metadata", http.StatusGatewayTimeout)
		return
	}

	var largestFile *torrent.File
	var maxSize int64
	for _, f := range t.Files() {
		if f.Length() > maxSize {
			maxSize = f.Length()
			largestFile = f
		}
	}

	if largestFile == nil {
		http.Error(w, "No files found", http.StatusNotFound)
		return
	}

	log.Printf("[Go Streamer] Streaming: %s (Size: %d)", largestFile.DisplayPath(), largestFile.Length())

	reader := largestFile.NewReader()
	reader.SetResponsive()
	defer reader.Close()

	http.ServeContent(w, r, largestFile.DisplayPath(), time.Now(), reader)
}
